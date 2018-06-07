/**
 * @author See Contributors.txt for code contributors and overview of BadgerDB.
 *
 *
 *Names: Raghav Bhagwat, Rishabh Chakravarty, Tej Lunani
 *
 *Wisc ID; bhagwat2, chakravarty3, lunani
 *
 *
 * @section LICENSE
 * Copyright (c) 2012 Database Group, Computer Sciences Department, University of Wisconsin-Madison.
 */

#include <memory>
#include <iostream>
#include "buffer.h"
#include "exceptions/buffer_exceeded_exception.h"
#include "exceptions/page_not_pinned_exception.h"
#include "exceptions/page_pinned_exception.h"
#include "exceptions/bad_buffer_exception.h"
#include "exceptions/hash_not_found_exception.h"

namespace badgerdb { 

BufMgr::BufMgr(std::uint32_t bufs)
	: numBufs(bufs) {
	bufDescTable = new BufDesc[bufs];

  for (FrameId i = 0; i < bufs; i++) 
  {
  	bufDescTable[i].frameNo = i;
  	bufDescTable[i].valid = false;
  }

  bufPool = new Page[bufs];

	int htsize = ((((int) (bufs * 1.2))*2)/2)+1;
  hashTable = new BufHashTbl (htsize);  // allocate the buffer hash table

  clockHand = bufs - 1;
}


BufMgr::~BufMgr() {
	
	for(uint32_t i=0; i<numBufs; i++)
	{
		BufDesc buf = bufDescTable[i];
		if(buf.dirty){
			flushFile(buf.file);
		}
	}
	
	delete [] bufPool;
	delete [] bufDescTable;
	delete hashTable;
}

//Advance clock to next frame in the buffer pool
void BufMgr::advanceClock()
{
	clockHand++;
	clockHand = clockHand % numBufs;
}

//Allocates a free frame using the clock algorithm; if necessary, writing a dirty page back
//to disk. Throws BufferExceededException if all buffer frames are pinned.
void BufMgr::allocBuf(FrameId & frame) 
{
	//Check if page has been found
	bool frameNF = true;
	//Store the frame being checked
	BufDesc buf;
	//Loop counter. Makes sure the while loop does not go to infinity
	uint32_t count = 0;
	
	while(frameNF && count <= numBufs){
		//Increment the clock
		advanceClock();
		//Increment the counter
		count++;
		//Get the current frame to be tested
		buf = bufDescTable[clockHand];
		
		if(buf.valid == false){
			frameNF = false;
		}
		else if(buf.refbit == true){
			//we must directly change the refbit value
			bufDescTable[clockHand].refbit = false;
		}
		else if(buf.pinCnt == 0){
			frameNF = false;
			hashTable->remove(buf.file, buf.pageNo);
			if(buf.dirty){
				bufDescTable[clockHand].file->writePage(bufPool[clockHand]);
				bufDescTable[clockHand].dirty= false;
			}
			bufDescTable[clockHand].Clear();
		}
	}
	
	if(frameNF){
		throw BufferExceededException();
	}

	frame = buf.frameNo;
}

//Reads a specific page. If the page is in the buffer, it will read it from there. If not
//the page will be loaded into the buffer pool.	
void BufMgr::readPage(File* file, const PageId pageNo, Page*& page)
{
	FrameId fno;
	try {
		// look for the page in the hashtable
		hashTable->lookup(file, pageNo, fno);
		// if found, increment the pin count, set the refbit to 0 and return the page
		bufDescTable[fno].pinCnt++;
		bufDescTable[fno].refbit = true;
		page = &bufPool[fno];
	}
	catch (HashNotFoundException e) {
		// If the page is not in hashtable, it means there was a buffer miss so we need to read from the disk and allocate a buffer frame to place the page
		allocBuf(fno);
		bufPool[fno] = file->readPage(pageNo);
		bufDescTable[fno].Set(file, pageNo);
		page = &bufPool[fno];
		hashTable->insert(file, pageNo, fno);
	}
}

//Decrements the pinCnt of the frame containing (file, PageNo) and, if dirty == true, sets
//the dirty bit. Throws PAGENOTPINNED if the pin count is already 0. Does nothing if
//page is not found in the hash table lookup.
void BufMgr::unPinPage(File* file, const PageId pageNo, const bool dirty) 
{
	FrameId fno;
	// look up hashtable
	hashTable->lookup(file, pageNo, fno);
	// if this page is already unpinned, throw exception
	if(bufDescTable[fno].pinCnt == 0)
		throw PageNotPinnedException("pageNotPinned", bufDescTable[fno].pageNo, fno);
	else
		bufDescTable[fno].pinCnt--; //Decrement the pin count
	if(dirty)
		bufDescTable[fno].dirty = true; //Set dirty
}

void BufMgr::flushFile(const File* file) 
{
	for(uint32_t i = 0; i < numBufs; i++){
		if(bufDescTable[i].file == file){
			if(!bufDescTable[i].valid){
				// if the frame is not valid, throw BadBufferException
				throw BadBufferException(i, bufDescTable[i].dirty, bufDescTable[i].valid, bufDescTable[i].refbit);
			}
			if(bufDescTable[i].pinCnt != 0){
				// if the frame is pinned, throw PagePinnedException
				throw PagePinnedException("pagePinned", bufDescTable[i].pageNo, i);
			}
			if(bufDescTable[i].dirty){
				// if the frame is dirty, write it to disk, then set dirty to false
				bufDescTable[i].file->writePage(bufPool[i]);
				bufDescTable[i].dirty = false;
			}
			// remove the page from hashtable
			hashTable->remove(file, bufDescTable[i].pageNo);
			// clear the buffer frame
			bufDescTable[i].Clear();
		}
	}
}

//This method will return a newly allocated page.
void BufMgr::allocPage(File* file, PageId &pageNo, Page*& page) 
{
	FrameId frameNum;

	Page p1 = file->allocatePage();
	allocBuf(frameNum);
	bufPool[frameNum] = p1;
	hashTable->insert(file,p1.page_number(), frameNum);
	bufDescTable[frameNum].Set(file,p1.page_number());
	pageNo = p1.page_number();
	page = &bufPool[frameNum];
}

//This method deletes a particular page from file.
void BufMgr::disposePage(File* file, const PageId PageNo)
{
	try {
		FrameId frameNum;
		hashTable->lookup(file, PageNo, frameNum);
		bufDescTable[frameNum].Clear();
		hashTable->remove(file, PageNo);
		file->deletePage(PageNo);
	} 
	catch (HashNotFoundException ex) {
		//Hash not found
	}
}

void BufMgr::printSelf(void) 
{
  BufDesc* tmpbuf;
	int validFrames = 0;
  
  for (std::uint32_t i = 0; i < numBufs; i++)
	{
  	tmpbuf = &(bufDescTable[i]);
		std::cout << "FrameNo:" << i << " ";
		tmpbuf->Print();

  	if (tmpbuf->valid == true)
    	validFrames++;
  }

	std::cout << "Total Number of Valid Frames:" << validFrames << "\n";
}

}
