#!/usr/bin/env python3
"""
STT Diagnostic Script
Run this to diagnose Speech-to-Text setup issues
"""

import os
import sys

print("="*70)
print("STT DIAGNOSTIC SCRIPT")
print("="*70)
print()

# Check 1: Python version
print("✓ Python Version:", sys.version.split()[0])
print()

# Check 2: Required packages
print("📦 Checking Python Packages...")
print("-"*70)

required_packages = {
    'vosk': 'vosk',
    'sounddevice': 'sounddevice',
    'numpy': 'numpy'
}

missing_packages = []
for package_name, import_name in required_packages.items():
    try:
        __import__(import_name)
        print(f"   ✅ {package_name} installed")
    except ImportError:
        print(f"   ❌ {package_name} NOT installed")
        missing_packages.append(package_name)

if missing_packages:
    print()
    print(f"⚠️  MISSING PACKAGES: {', '.join(missing_packages)}")
    print(f"   Install with: pip install {' '.join(missing_packages)}")
else:
    print("   ✅ All required packages installed")
print()

# Check 3: Model directory
print("📁 Checking Vosk Model...")
print("-"*70)

from config import STT_MODEL_PATH

print(f"   Model path from config: {STT_MODEL_PATH}")
print()

# Check if model path exists
if os.path.exists(STT_MODEL_PATH):
    print(f"   ✅ Model directory exists: {STT_MODEL_PATH}")
    
    # Check if it's a directory
    if os.path.isdir(STT_MODEL_PATH):
        print(f"   ✅ Path is a directory")
        
        # List contents
        contents = os.listdir(STT_MODEL_PATH)
        print(f"   📂 Contents: {contents}")
        print()
        
        # Check for required subdirectories
        required_dirs = ['am', 'graph', 'conf']
        required_files = ['ivector']  # Could be dir or symlink
        
        print("   Checking model structure...")
        all_good = True
        
        for req_dir in required_dirs:
            dir_path = os.path.join(STT_MODEL_PATH, req_dir)
            if os.path.exists(dir_path):
                print(f"      ✅ {req_dir}/ found")
            else:
                print(f"      ❌ {req_dir}/ MISSING")
                all_good = False
        
        # Check ivector (can be dir or symlink)
        ivector_path = os.path.join(STT_MODEL_PATH, 'ivector')
        if os.path.exists(ivector_path):
            print(f"      ✅ ivector found")
        else:
            print(f"      ⚠️  ivector not found (optional for some models)")
        
        if all_good:
            print()
            print("   ✅ Model structure looks correct!")
        else:
            print()
            print("   ❌ Model structure incomplete!")
            print("   💡 The model might be corrupted or not fully extracted")
            print("   💡 Try re-downloading and extracting the model")
    else:
        print(f"   ❌ Path exists but is NOT a directory")
        all_good = False
else:
    print(f"   ❌ Model directory NOT FOUND: {STT_MODEL_PATH}")
    print()
    print("   💡 Possible issues:")
    print("      1. Model not downloaded")
    print("      2. Model in wrong location")
    print("      3. Model folder has different name")
    print()
    print("   🔍 Searching for potential model directories...")
    
    # Search for potential model directories
    for item in os.listdir('.'):
        if os.path.isdir(item) and 'vosk' in item.lower():
            print(f"      📁 Found: {item}")
            print(f"         Rename with: mv {item} {STT_MODEL_PATH}")
    
    all_good = False

print()

# Check 4: Try to load model (if vosk is installed and model exists)
if 'vosk' not in missing_packages and os.path.exists(STT_MODEL_PATH):
    print("🧪 Testing Model Loading...")
    print("-"*70)
    try:
        from vosk import Model
        print(f"   Loading model from: {STT_MODEL_PATH}")
        model = Model(STT_MODEL_PATH)
        print("   ✅ Model loaded successfully!")
        print()
        all_good = True
    except Exception as e:
        print(f"   ❌ Model loading FAILED!")
        print(f"   Error: {e}")
        print()
        print("   💡 Possible fixes:")
        print("      1. Model is corrupted - re-download")
        print("      2. Model structure incomplete - check extraction")
        print("      3. Model version incompatible with vosk version")
        all_good = False

# Check 5: Audio devices
print()
if 'sounddevice' not in missing_packages:
    print("🎤 Checking Audio Devices...")
    print("-"*70)
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        
        input_devices = [d for i, d in enumerate(devices) if d['max_input_channels'] > 0]
        
        if input_devices:
            print(f"   ✅ Found {len(input_devices)} input device(s):")
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    default_marker = ""
                    
                    # Check if this is the default device
                    try:
                        if hasattr(sd.default.device, 'input'):
                            default_idx = sd.default.device.input
                        elif isinstance(sd.default.device, tuple):
                            default_idx = sd.default.device[0]
                        else:
                            default_idx = sd.default.device
                        
                        if i == default_idx:
                            default_marker = " ⭐ DEFAULT"
                    except:
                        pass
                    
                    print(f"      [{i}] {device['name']}{default_marker}")
                    print(f"          Channels: {device['max_input_channels']}, Sample Rate: {device['default_samplerate']}")
        else:
            print("   ⚠️  No input devices found")
            print("   💡 Make sure USB microphone is connected")
        print()
    except Exception as e:
        print(f"   ❌ Error checking audio devices: {e}")
        print("   💡 You may need to install: sudo apt-get install portaudio19-dev")
        print()

# Summary
print()
print("="*70)
print("SUMMARY")
print("="*70)

if all_good and not missing_packages:
    print("✅ All checks passed! STT should work.")
    print()
    print("If you still get errors, check:")
    print("   1. Run: python main.py")
    print("   2. Look for specific error messages")
    print("   3. Check permissions: ls -la vosk-model-*")
else:
    print("❌ Issues found. Fix the problems above and try again.")
    print()
    print("Quick Fix Checklist:")
    if missing_packages:
        print(f"   □ Install packages: pip install {' '.join(missing_packages)}")
    if not os.path.exists(STT_MODEL_PATH):
        print(f"   □ Download model: wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
        print(f"   □ Extract: unzip vosk-model-small-en-us-0.15.zip")
        print(f"   □ Rename: mv vosk-model-small-en-us-0.15 {STT_MODEL_PATH}")
    print("   □ Connect USB microphone")
    print("   □ Install system packages: sudo apt-get install portaudio19-dev")

print("="*70)

