from typing import Required
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, Profile


class ProfileSerializer(serializers.Serializer):
    class meta:
        model=Profile
        fields=[
            'id',
            'phone',
            'address',
            'bio',
            'profile_image',
            'created_at',
            'updated_at'
        ]
        read_only_fields=['id', 'created_at', 'updated_at']

class UserSerializer(serializers.Serializer):
    """Serializers for GET requests only"""
    profile=ProfileSerializer(read_only=True)
    full_name=serializers.CharField(source='get_full_name', read_only=True)

    class meta:
        model=User
        fields=[
            'id',
            'email',
            'first_name',
            'last_name',
            'role',
            'is_verified',
            'is_active',
            'date_joined',
            'profile'
        ]
        read_only_fields = [
            'id',
            'is_verified',
            'is_active',
            'date_joined'
        ]

class UserRegisterationSerializer(serializers.Serializer):
    """For user registeration"""
    password=serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    confirm_password=serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class meta:
        model=User
        fields=[
            'email',
            'password',
            'confirm_password',
            'first_name',
            'last_name',
            'role',
        ]
        extra_kwargs={
            'first_name': {'required': True},
            'last_name' : {'required': True}
        }

    def validate_role(self,value):
        """Prevents the user to register as an admin"""
        if value == User.Admin:
            raise serializers.ValidationError(
            "Cannot register as admin. Please contact support."
            )
        return value
    
    def validate_email(self, value):
        """checks if an email already exists"""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError(
                "A user with this email already exists"
            )
        return value.lower()
    
    def validate_password(self,attrs):
        """validates passwords match and strength"""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
            "password_confirm": "Passwords do not match."
            }
            )
        
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({
                "password": list(e.messages)
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create user with encrypted password"""
        validated_data.pop('confirm_password')
        user=User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role=validated_data.get('role', User.Individual)
        )

        return user

class UserProfileUpdateSerializer(serializers.Serializer):
        """
        Combined serializer for updating both User and Profile in one request
        Useful when user wants to update everything at once from one form
        """
        profile=ProfileSerializer(required=False)

        class meta:
            profile=User
            fields=[
                'first_name',
                'last_name',
                'profile'
            ]
            
        def update(self, instance, validated_data):
            """update user info and profile together"""
            profile_data=validated_data.pop('profile', None)

            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # Update profile if data provided
            if profile_data and hasattr(instance, 'profile'):
                profile = instance.profile
                for attr, value in profile_data.items():
                    setattr(profile, attr, value)
                profile.save()
        
            return instance

class ChangeOldPasswordSerializer(serializers.Serializer):
        """serialzer for changing password"""
        old_password=serializers.CharField(
            required=True,
            write_only=True,
            style={'input_type': 'password'}
        )
        new_password = serializers.CharField(
            required=True,
            write_only=True,
            style={'input_type': 'password'}
        )
        new_password_confirm = serializers.CharField(required=True,
            write_only=True,
            style={'input_type': 'password'}
        )

        def validate_old_password(self, value):
            """Check if old password is correct"""
            user = self.context['request'].user
            if not user.check_password(value):
                raise serializers.ValidationError("Old password is incorrect.")
            return value
        
        def validate(self, attrs):
            """Validate new password confirmation"""
            if attrs['new_password'] != attrs['new_password_confirm']:
                raise serializers.ValidationError({
                    "new_password_confirm": "New passwords do not match."
                })
            
            # Validate password strength
            try:
                validate_password(attrs['new_password'])
            except ValidationError as e:
                raise serializers.ValidationError({
                    "new_password": list(e.messages)
                })
            
            return attrs
        

        def save(self):
            """Set new password"""
            user = self.context['request'].user
            user.set_password(self.validated_data['new_password'])
            user.save()
            return user

class RoleChoicesSerializer(serializers.Serializer):
    """Serializer to return available role choices"""
    
    value = serializers.CharField()
    label = serializers.CharField()

class ProfileImageUploadSerializer(serializers.ModelSerializer):
    """Serializer for profile image upload"""
    
    class Meta:
        model = Profile
        fields = ['profile_image']
    
    def validate_profile_image(self, value):
        """Validate image size and format"""
        # Check file size (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "Image file size cannot exceed 5MB."
            )
        
        # Check file format
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File format not supported. Allowed: {', '.join(allowed_extensions)}"
            )
        
        return value

class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for user lists"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    profile_image = serializers.ImageField(source='profile.profile_image', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'is_verified',
            'profile_image'
        ]