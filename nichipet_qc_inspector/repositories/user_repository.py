from nichipet_qc_inspector.models.db import AppUser


class UserRepository:
    def __init__(self, session):
        self.session = session

    def get_by_username(self, username: str):
        return (
            self.session.query(AppUser)
            .filter(AppUser.username == username)
            .first()
        )

    def get_by_id(self, user_id: int):
        return (
            self.session.query(AppUser)
            .filter(AppUser.id == user_id)
            .first()
        )

    def list_users(self):
        return (
            self.session.query(AppUser)
            .order_by(AppUser.username.asc())
            .all()
        )

    def create_user(self, username: str, password_hash: str, role: str = "user", is_active: bool = True):
        user = AppUser(
            username=username,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update_role(self, user_id: int, role: str):
        user = self.get_by_id(user_id)
        if user is None:
            return None
        user.role = role
        self.session.commit()
        self.session.refresh(user)
        return user

    def update_password(self, user_id: int, password_hash: str):
        user = self.get_by_id(user_id)
        if user is None:
            return None
        user.password_hash = password_hash
        self.session.commit()
        self.session.refresh(user)
        return user

    def set_active(self, user_id: int, is_active: bool):
        user = self.get_by_id(user_id)
        if user is None:
            return None
        user.is_active = is_active
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete_user(self, user_id: int):
        user = self.get_by_id(user_id)
        if user is None:
            return False
        self.session.delete(user)
        self.session.commit()
        return True