"""
Face Recognition Router - API endpoints for face recognition
"""

from fastapi import APIRouter, HTTPException
from typing import List
from schemas_face import (
    FaceRecognitionRequest,
    FaceRecognitionResponse,
    FamilyMember
)
from services.face_recognition_service import get_face_recognition_service

router = APIRouter(prefix="/face", tags=["face_recognition"])


@router.post("/recognize", response_model=FaceRecognitionResponse)
async def recognize_face(request: FaceRecognitionRequest):
    """
    Recognize a face from a base64-encoded image.
    
    This endpoint sends the image to the Lambda face recognition API
    and returns the matched family member if found.
    
    **Request Body:**
    - `image_base64`: Base64-encoded image string (required)
    - `min_confidence`: Minimum confidence threshold 0-100 (optional, default: 85)
    
    **Response:**
    - `recognized`: Boolean indicating if a match was found
    - `match`: Match details including face ID, similarity, and metadata
    - `name`: Name of recognized person (if found)
    - `relationship`: Relationship to user (if found)
    - `similarity`: Confidence score 0-100
    
    **Example Usage:**
    ```bash
    curl -X POST http://localhost:8000/face/recognize \\
      -H "Content-Type: application/json" \\
      -d '{
        "image_base64": "data:image/jpeg;base64,/9j/4AAQ...",
        "min_confidence": 85
      }'
    ```
    """
    try:
        face_service = get_face_recognition_service()
        
        result = await face_service.recognize_face(
            image_base64=request.image_base64,
            min_confidence=request.min_confidence
        )
        
        # Print recognition result to console
        print("\n" + "="*60)
        print("🔍 FACE RECOGNITION RESULT")
        print("="*60)
        
        if result.get("recognized"):
            print(f"✅ Face Recognized!")
            print(f"   Name: {result.get('name')}")
            print(f"   Relationship: {result.get('relationship')}")
            print(f"   Similarity: {result.get('similarity'):.2f}%")
            print(f"   Family Member ID: {result.get('family_member_id')}")
        else:
            print("❌ No face recognized")
            print(f"   No matching family member found in database")
        
        print("="*60 + "\n")
        
        return FaceRecognitionResponse(**result)
        
    except Exception as e:
        print(f"❌ Error during face recognition: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Face recognition failed: {str(e)}"
        )


@router.get("/family", response_model=List[FamilyMember])
async def list_family_members():
    """
    Get all registered family members for the user.
    
    This endpoint fetches all family members that have been registered
    in the face recognition system.
    
    **Response:**
    - List of family members with their details:
      - `familyMemberId`: Unique identifier
      - `name`: Person's name
      - `relationship`: Relationship to user (e.g., "Father", "Mother")
      - `photoUrl`: URL to the person's photo
      - `rekognitionFaceId`: AWS Rekognition face ID
      - `createdAt`: Registration timestamp
    
    **Example Usage:**
    ```bash
    curl http://localhost:8000/face/family
    ```
    """
    try:
        face_service = get_face_recognition_service()
        family_members = await face_service.get_family_members()
        
        # Print family members to console
        print("\n" + "="*60)
        print("👨‍👩‍👧‍👦 FAMILY MEMBERS")
        print("="*60)
        
        if family_members:
            for i, member in enumerate(family_members, 1):
                print(f"{i}. {member.get('name')} - {member.get('relationship')}")
                print(f"   ID: {member.get('familyMemberId')}")
                print(f"   Photo: {member.get('photoUrl', 'N/A')}")
                print()
        else:
            print("No family members registered yet")
        
        print("="*60 + "\n")
        
        return [FamilyMember(**member) for member in family_members]
        
    except Exception as e:
        print(f"❌ Error fetching family members: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch family members: {str(e)}"
        )


@router.get("/status")
async def get_face_recognition_status():
    """
    Get the status of the face recognition service.
    
    This endpoint checks if the face recognition Lambda API is configured
    and accessible.
    
    **Response:**
    - `configured`: Whether the Lambda API URL is configured
    - `api_url`: The configured Lambda API URL (without sensitive parts)
    
    **Example Usage:**
    ```bash
    curl http://localhost:8000/face/status
    ```
    """
    from config import LAMBDA_API_URL
    
    configured = bool(LAMBDA_API_URL)
    
    return {
        "configured": configured,
        "api_url": LAMBDA_API_URL if configured else None,
        "message": "Face recognition service is configured and ready" if configured else "Lambda API URL not configured in .env"
    }

