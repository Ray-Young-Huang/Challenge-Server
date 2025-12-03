from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool

# SQLite数据库文件路径
SQLALCHEMY_DATABASE_URL = "sqlite:///./challenge_server.db"

# 创建数据库引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

# 创建会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 定义数据库模型
class TeamRegistration(Base):
    __tablename__ = "team_registrations"
    
    id = Column(Integer, primary_key=True, index=True)
    teamName = Column(String, nullable=False)
    organization = Column(String, nullable=False)
    orgAddress = Column(String, default="")
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)  # 实际应用中应该加密存储
    
    # 关联成员
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")

class TeamMember(Base):
    __tablename__ = "team_members"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("team_registrations.id"))
    name = Column(String, nullable=False)
    isLeader = Column(Boolean, default=False)
    
    # 关联团队
    team = relationship("TeamRegistration", back_populates="members")

# 创建所有表
def init_db():
    Base.metadata.create_all(bind=engine)

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
