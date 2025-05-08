from sqlalchemy import Column, String, JSON, create_engine
from sqlalchemy.orm import relationship, declarative_base
from werkzeug.security import check_password_hash

#Create the database
Base = declarative_base()

class User(Base):
    __tablename__ = 'userdetails'
    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    preferences = Column(JSON, nullable=True)
    location = Column(String, nullable=True)

    # Check if the password is correct
    def check_password(self, password):
        return check_password_hash(self.password, password)

engine = create_engine('sqlite:///userdata.db')
Base.metadata.create_all(engine)

print('Database created successfully.')