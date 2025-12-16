"""Quick script to check or reset admin password"""
import asyncio
from backend.database import AsyncSessionLocal
from backend import models
from backend.auth.service import get_password_hash
from sqlalchemy import select

async def check_admin():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(models.User).where(models.User.is_admin == True))
        admin = result.scalar_one_or_none()
        if admin:
            print(f"Admin user found: {admin.username}")
            print(f"Must change password: {admin.must_change_password}")
        else:
            print("No admin user found")
            # Create admin
            admin_user = models.User(
                username="admin",
                hashed_password=get_password_hash("admin"),
                is_admin=True,
                must_change_password=False
            )
            db.add(admin_user)
            await db.commit()
            print("Created admin user with username: admin, password: admin")

if __name__ == "__main__":
    asyncio.run(check_admin())


