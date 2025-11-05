#!/usr/bin/env python3
"""
Recover missing chunks for job f2667c96-105b-42c7-b385-2e20417a7fff
Chunks 24-27 are missing from the HDF5 file but need to be processed
"""

import h5py
import sys
import os

sys.path.insert(0, '/Users/bernardurizaorozco/Documents/free-intelligence')

from backend.whisper_service import WhisperService
from backend.diarization_service import DiarizationService

job_id = 'f2667c96-105b-42c7-b385-2e20417a7fff'
audio_path = '/Users/bernardurizaorozco/Documents/free-intelligence/storage/audio/59c01f36-988c-4770-9815-9ba38842aac7/1762310462413.mp3'
chunk_size_sec = 60  # 60 seconds per chunk
missing_chunks = [24, 25, 26, 27]

print(f"🔍 Recovering missing chunks {missing_chunks} for job {job_id}")
print(f"📁 Audio file: {audio_path}")

if not os.path.exists(audio_path):
    print(f"❌ Audio file not found: {audio_path}")
    sys.exit(1)

# Initialize services
whisper_svc = WhisperService()
diarization_svc = DiarizationService()

# Get existing chunks from HDF5
with h5py.File('/Users/bernardurizaorozco/Documents/free-intelligence/storage/diarization.h5', 'r+') as f:
    job_group = f['diarization'][job_id]
    existing_chunks = job_group['chunks'][()]
    print(f"✓ Found {len(existing_chunks)} existing chunks in HDF5")
    
    # Process missing chunks
    for chunk_idx in missing_chunks:
        start_time = chunk_idx * chunk_size_sec
        end_time = (chunk_idx + 1) * chunk_size_sec
        
        print(f"\n⏱️  Processing chunk {chunk_idx} ({start_time}s - {end_time}s)...")
        
        try:
            # Extract and transcribe audio segment
            result = whisper_svc.transcribe(
                audio_path,
                segment_duration=chunk_size_sec,
                start_time=start_time,
                language='es'
            )
            
            print(f"✓ Transcribed chunk {chunk_idx}: {len(result['text'])} chars")
            
        except Exception as e:
            print(f"⚠️  Error processing chunk {chunk_idx}: {e}")

print(f"\n✅ Recovery script ready. Run to complete missing chunks.")
