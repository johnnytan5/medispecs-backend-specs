"""
Face Recognition Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional


class FaceRecognitionRequest(BaseModel):
    """Request schema for face recognition"""
    image_base64: str = Field(..., description="Base64-encoded image string")
    min_confidence: Optional[float] = Field(85.0, ge=0.0, le=100.0, description="Minimum confidence threshold (0-100)")


class FaceMetadata(BaseModel):
    """Metadata for a recognized face"""
    family_member_id: Optional[str] = Field(None, alias="familyMemberId")
    name: Optional[str] = None
    relationship: Optional[str] = None
    photo_s3_key: Optional[str] = Field(None, alias="photoS3Key")
    user_id: Optional[str] = Field(None, alias="userId")
    
    class Config:
        populate_by_name = True


class FaceMatch(BaseModel):
    """Face match details"""
    face_id: Optional[str] = Field(None, alias="faceId")
    similarity: Optional[float] = None
    metadata: Optional[FaceMetadata] = None
    
    class Config:
        populate_by_name = True


class FaceRecognitionResponse(BaseModel):
    """Response schema for face recognition"""
    match: Optional[FaceMatch] = None
    recognized: bool = False
    similarity: Optional[float] = None
    name: Optional[str] = None
    relationship: Optional[str] = None
    family_member_id: Optional[str] = None


class FamilyMember(BaseModel):
    """Family member details"""
    family_member_id: Optional[str] = Field(None, alias="familyMemberId")
    name: Optional[str] = None
    relationship: Optional[str] = None
    photo_s3_key: Optional[str] = Field(None, alias="photoS3Key")
    photo_url: Optional[str] = Field(None, alias="photoUrl")
    rekognition_face_id: Optional[str] = Field(None, alias="rekognitionFaceId")
    created_at: Optional[str] = Field(None, alias="createdAt")
    
    class Config:
        populate_by_name = True

