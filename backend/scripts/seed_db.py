#!/usr/bin/env python3
"""
Database Seed Script

Creates initial users and data for the Qenergyz application.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from api.models.database import AsyncSessionLocal, init_database
from api.models.user import User, UserRole
from api.dependencies.auth import PasswordHandler
from api.utils.config import get_settings
import structlog

logger = structlog.get_logger(__name__)


async def create_admin_user():
    """Create default admin user"""
    async with AsyncSessionLocal() as session:
        try:
            # Check if admin user already exists
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.email == "admin@qenergyz.com")
            )
            existing_admin = result.scalar_one_or_none()
            
            if existing_admin:
                logger.info("Admin user already exists")
                return existing_admin
            
            # Create admin user
            admin_user = User(
                email="admin@qenergyz.com",
                password_hash=PasswordHandler.hash_password("AdminPassword123!"),
                first_name="System",
                last_name="Administrator",
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                is_verified=True,
                company="Qenergyz",
                job_title="System Administrator",
                region="middle_east",
                kyc_status="approved"
            )
            
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            
            logger.info("Admin user created successfully", user_id=admin_user.id)
            return admin_user
            
        except Exception as e:
            await session.rollback()
            logger.error("Failed to create admin user", error=str(e))
            raise


async def create_demo_users():
    """Create demo users for development"""
    demo_users_data = [
        {
            "email": "trader@qenergyz.com",
            "password": "TraderPassword123!",
            "first_name": "John",
            "last_name": "Trader", 
            "role": UserRole.TRADER,
            "company": "Qenergyz Trading",
            "job_title": "Senior Energy Trader"
        },
        {
            "email": "manager@qenergyz.com", 
            "password": "ManagerPassword123!",
            "first_name": "Sarah",
            "last_name": "Manager",
            "role": UserRole.MANAGER,
            "company": "Qenergyz Management",
            "job_title": "Trading Manager"
        },
        {
            "email": "user@qenergyz.com",
            "password": "UserPassword123!",
            "first_name": "Mike",
            "last_name": "User",
            "role": UserRole.USER,
            "company": "Qenergyz Corp",
            "job_title": "Energy Analyst"
        }
    ]
    
    async with AsyncSessionLocal() as session:
        created_users = []
        
        for user_data in demo_users_data:
            try:
                # Check if user already exists
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(User.email == user_data["email"])
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    logger.info("Demo user already exists", email=user_data["email"])
                    continue
                
                # Create demo user
                demo_user = User(
                    email=user_data["email"],
                    password_hash=PasswordHandler.hash_password(user_data["password"]),
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    role=user_data["role"],
                    is_active=True,
                    is_verified=True,
                    company=user_data["company"],
                    job_title=user_data["job_title"],
                    region="middle_east",
                    kyc_status="approved" if user_data["role"] != UserRole.USER else "pending"
                )
                
                session.add(demo_user)
                created_users.append(demo_user)
                
                logger.info("Demo user created", email=user_data["email"], role=user_data["role"].value)
                
            except Exception as e:
                logger.error("Failed to create demo user", email=user_data["email"], error=str(e))
        
        if created_users:
            await session.commit()
            logger.info(f"Created {len(created_users)} demo users")
        
        return created_users


async def main():
    """Main seed function"""
    try:
        logger.info("Starting database seeding")
        
        # Initialize database
        await init_database()
        logger.info("Database initialized")
        
        # Create admin user
        admin = await create_admin_user()
        
        # Create demo users
        demo_users = await create_demo_users()
        
        logger.info(
            "Database seeding completed successfully",
            admin_created=bool(admin),
            demo_users_created=len(demo_users)
        )
        
        print("\n✅ Database seeding completed!")
        print(f"✅ Admin user: admin@qenergyz.com / AdminPassword123!")
        print(f"✅ Trader user: trader@qenergyz.com / TraderPassword123!")
        print(f"✅ Manager user: manager@qenergyz.com / ManagerPassword123!")
        print(f"✅ Regular user: user@qenergyz.com / UserPassword123!")
        print("\n⚠️  Please change these default passwords in production!")
        
    except Exception as e:
        logger.error("Database seeding failed", error=str(e))
        print(f"❌ Database seeding failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())