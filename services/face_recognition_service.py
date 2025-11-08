"""
Face Recognition Service - Interact with Lambda Face Recognition API

This service handles face recognition by sending images to the Lambda API
and processing the recognition results.
"""

import httpx
from typing import Optional, Dict, Any
from config import LAMBDA_API_URL, USER_ID


class FaceRecognitionService:
    """Service for face recognition operations"""
    
    def __init__(self, api_url: str = LAMBDA_API_URL):
        self.api_url = api_url.rstrip('/') if api_url else ""
        self.user_id = USER_ID
    
    async def recognize_face(
        self, 
        image_base64: str, 
        min_confidence: float = 85.0
    ) -> Dict[str, Any]:
        """
        Recognize a face from a base64-encoded image.
        
        Args:
            image_base64: Base64-encoded image string (with or without data URI prefix)
            min_confidence: Minimum confidence threshold (0-100), default 85
        
        Returns:
            Dictionary with recognition results:
            {
                "match": {
                    "faceId": "...",
                    "similarity": 95.5,
                    "metadata": {
                        "familyMemberId": "fam_abc123",
                        "name": "John Doe",
                        "relationship": "Father",
                        "photoS3Key": "family/u_123/fam_abc123.jpg",
                        "userId": "u_123"
                    }
                } or None if no match
            }
        
        Raises:
            httpx.HTTPError: If API request fails
            ValueError: If response is invalid
        """
        url = f"{self.api_url}/recognize"
        
        payload = {
            "userId": self.user_id,
            "imageBase64": image_base64,
            "minConfidence": min_confidence
        }
        
        print(f"🔍 Sending face recognition request to Lambda API...")
        print(f"   URL: {url}")
        print(f"   User ID: {self.user_id}")
        print(f"   Min Confidence: {min_confidence}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            
            # Log response for debugging
            if response.status_code != 200:
                print(f"❌ Lambda API Error (Status {response.status_code})")
                try:
                    error_detail = response.json()
                    print(f"   Error details: {error_detail}")
                except:
                    print(f"   Response text: {response.text}")
            
            response.raise_for_status()
            
            result = response.json()
            
            # Check if match was found
            match = result.get("match")
            
            if match is None:
                print("❌ No face match found")
                return {"match": None, "recognized": False}
            
            # Extract match details
            similarity = match.get("similarity", 0)
            metadata = match.get("metadata")
            
            if metadata:
                print(f"✅ Face recognized!")
                print(f"   Name: {metadata.get('name')}")
                print(f"   Relationship: {metadata.get('relationship')}")
                print(f"   Similarity: {similarity:.2f}%")
                print(f"   Family ID: {metadata.get('familyMemberId')}")
            else:
                print(f"⚠️  Face matched (similarity: {similarity:.2f}%) but no metadata found")
            
            return {
                "match": match,
                "recognized": metadata is not None,
                "similarity": similarity,
                "name": metadata.get("name") if metadata else None,
                "relationship": metadata.get("relationship") if metadata else None,
                "family_member_id": metadata.get("familyMemberId") if metadata else None,
            }
    
    async def get_family_members(self) -> list:
        """
        Get all family members for the user.
        
        Returns:
            List of family members with their details
        """
        url = f"{self.api_url}/family"
        
        params = {"userId": self.user_id}
        
        print(f"👨‍👩‍👧‍👦 Fetching family members from Lambda API...")
        print(f"   URL: {url}")
        print(f"   User ID: {self.user_id}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            family_members = response.json()
            
            print(f"✅ Retrieved {len(family_members)} family member(s)")
            for member in family_members:
                print(f"   - {member.get('name')} ({member.get('relationship')})")
            
            return family_members


# Global service instance
_face_service_instance: Optional[FaceRecognitionService] = None


def get_face_recognition_service() -> FaceRecognitionService:
    """Get the global face recognition service instance"""
    global _face_service_instance
    if _face_service_instance is None:
        _face_service_instance = FaceRecognitionService()
    return _face_service_instance

