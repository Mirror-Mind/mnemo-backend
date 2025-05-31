import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import requests
from sqlalchemy.orm import Session

from helpers.logger_config import logger
from models.user_models import Account, SessionLocal, User, UserThread, Waitlist


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_phone_number(self, phone_number: str) -> Optional[User]:
        # Normalize phone number: remove first two chars if length > 10
        if phone_number and len(phone_number) > 10:
            phone_number = phone_number[3:]
        return self.db.query(User).filter(User.phoneNumber == phone_number).first()

    def get_users_with_google_token(self) -> List[User]:
        """Get all users who have a valid Google access token."""
        try:
            # Join User and Account tables to get users with Google accounts
            users = (
                self.db.query(User)
                .join(Account)
                .filter(
                    Account.providerId == "google",
                    Account.accessToken.isnot(None),
                    User.phoneNumber.isnot(None),  # Only get users with phone numbers
                )
                .all()
            )
            return users
        except Exception as e:
            logger.error(f"Error getting users with Google token: {str(e)}")
            return []

    def get_google_access_token(self, user_id: str) -> Optional[str]:
        account = (
            self.db.query(Account)
            .filter(Account.userId == user_id, Account.providerId == "google")
            .first()
        )
        if not account:
            print(f"No Google account found for user {user_id}")
            return None
        if account.accessToken:
            # Check if the current access token is valid
            token_info_url = f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={account.accessToken}"
            response = requests.get(token_info_url)
            if response.status_code == 200:
                logger.info("Current access token is valid")
                return account.accessToken

        # If no access token or token is invalid, try to refresh
        if account.refreshToken:
            logger.info("\nAttempting to refresh token using refresh token")
            refresh_url = "https://oauth2.googleapis.com/token"
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            payload = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": account.refreshToken,
                "grant_type": "refresh_token",
            }
            response = requests.post(refresh_url, data=payload)
            if response.status_code == 200:
                new_tokens = response.json()
                account.accessToken = new_tokens["access_token"]
                if "refresh_token" in new_tokens:
                    account.refreshToken = new_tokens["refresh_token"]
                self.db.commit()
                self.db.refresh(account)
                logger.info("Successfully refreshed access token")
                return account.accessToken
            else:
                logger.error(
                    f"Failed to refresh token. Status: {response.status_code}, Response: {response.text}"
                )
                return None

        return None

    def get_github_access_token(self, user_id: str) -> Optional[str]:
        account = (
            self.db.query(Account)
            .filter(Account.userId == user_id, Account.providerId == "github")
            .first()
        )
        return account.accessToken if account else None

    def get_google_refresh_token(self, user_id: str) -> Optional[str]:
        account = (
            self.db.query(Account)
            .filter(Account.userId == user_id, Account.providerId == "google")
            .first()
        )
        return account.refreshToken if account else None

    def get_access_token_by_phone_number(self, phone_number: str) -> Optional[str]:
        user = self.get_user_by_phone_number(phone_number)
        if not user:
            return None
        account = self.db.query(Account).filter(Account.userId == user.id).first()
        return account.accessToken if account else None

    def is_user_in_waitlist(self, email: str) -> bool:
        return (
            self.db.query(Waitlist).filter(Waitlist.email == email).first() is not None
        )

    def create_user_thread(
        self, user_id: str, thread_id: str, checkpoint: Optional[str] = None
    ) -> UserThread:
        db_user_thread = UserThread(
            userId=user_id, threadId=thread_id, checkpoint=checkpoint
        )
        self.db.add(db_user_thread)
        self.db.commit()
        self.db.refresh(db_user_thread)
        return db_user_thread

    def get_user_thread(self, user_id: str) -> Optional[UserThread]:
        return self.db.query(UserThread).filter(UserThread.userId == user_id).first()

    def update_user_thread_checkpoint(
        self, user_id: str, checkpoint: str
    ) -> Optional[UserThread]:
        db_user_thread = self.get_user_thread(user_id)
        if db_user_thread:
            db_user_thread.checkpoint = checkpoint
            self.db.commit()
            self.db.refresh(db_user_thread)
        return db_user_thread

    def create_user(
        self,
        id: str,
        name: str,
        email: str,
        image: Optional[str] = None,
        phone_number: Optional[str] = None,
        lang: Optional[str] = None,
    ) -> User:
        db_user = User(
            id=id,
            name=name,
            email=email,
            image=image,
            phoneNumber=phone_number,
            lang=lang,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def create_or_update_google_account(
        self, user_id: str, account_id: str, access_token: str, refresh_token: str
    ) -> Account:
        account = (
            self.db.query(Account)
            .filter(Account.userId == user_id, Account.providerId == "google")
            .first()
        )
        if account:
            account.accessToken = access_token
            account.refreshToken = refresh_token
            account.updatedAt = datetime.now(timezone.utc)
        else:
            account = Account(
                id=str(uuid.uuid4()),
                accountId=account_id,
                providerId="google",
                userId=user_id,
                accessToken=access_token,
                refreshToken=refresh_token,
            )
            self.db.add(account)

        self.db.commit()
        self.db.refresh(account)
        return account


# Example Usage (for testing - ensure DATABASE_URL is in your .env)
if __name__ == "__main__":
    import os
    import uuid
    from datetime import datetime, timezone

    from dotenv import load_dotenv

    from models.user_models import Base, engine

    load_dotenv()
    # Create tables if they don't exist (for local testing)
    # In a real app, you'd use Alembic for migrations
    Base.metadata.create_all(bind=engine)

    db_session = SessionLocal()  # Create a session for the example
    try:
        repo = UserRepository(db=db_session)

        # Test Google Account Token Refresh
        test_user_id = "lPC3YhpW8XHTFG5qxfQ98aoApS09QZy4"

        # First check if user and account exist
        test_user = repo.get_user_by_id(test_user_id)
        if not test_user:
            print(f"Error: Test user with ID {test_user_id} not found")
            exit(1)

        print(f"\nTesting token refresh for user: {test_user_id}")
        print(f"User found: {test_user.name} ({test_user.email})")

        # Get existing account
        account = (
            repo.db.query(Account)
            .filter(Account.userId == test_user_id, Account.providerId == "google")
            .first()
        )
        if not account:
            print(f"Error: No Google account found for user {test_user_id}")
            exit(1)

        print(f"Found existing Google account with ID: {account.id}")
        print(
            f"Current access token: {account.accessToken[:20] if account.accessToken else 'None'}... (truncated)"
        )
        print(
            f"Current refresh token: {account.refreshToken[:20] if account.refreshToken else 'None'}... (truncated)"
        )

        # Now test the token refresh logic
        print("\nAttempting to validate/refresh Google access token")
        refreshed_token = repo.get_google_access_token(test_user_id)
        if refreshed_token:
            print(
                f"Successfully retrieved/refreshed Google access token: {refreshed_token[:20]}... (truncated)"
            )
        else:
            print(
                f"Failed to retrieve/refresh Google access token for user: {test_user_id}"
            )

    finally:
        db_session.close()  # Close the session for the example
