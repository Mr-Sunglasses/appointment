from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware

# database
from sqlalchemy.orm import Session
from .database import repo, models, schemas
from .database.database import SessionLocal, engine
models.Base.metadata.create_all(bind=engine)

# authentication
from .controller.auth import Auth

# init app
app = FastAPI()

# allow requests from own frontend running on a different port
app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:8080"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

def get_db():
  """run database session"""
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


@app.get("/login")
def login(db: Session = Depends(get_db)):
  """endpoint to get authentication status of current user"""
  me = Auth(db).subscriber
  return me is not None


@app.post("/me", response_model=schemas.Subscriber)
def create_me(subscriber: schemas.SubscriberBase, db: Session = Depends(get_db)):
  """endpoint to add an authenticated subscriber to db, if they doesn't exist yet"""
  email_exists = repo.get_subscriber_by_email(db=db, email=subscriber.email)
  if email_exists:
    raise HTTPException(status_code=400, detail="Email already registered")
  username_exists = repo.get_subscriber_by_username(db=db, username=subscriber.username)
  if username_exists:
    raise HTTPException(status_code=400, detail="Username already registered")
  return repo.create_subscriber(db=db, subscriber=subscriber)


@app.get("/me", response_model=schemas.Subscriber)
def read_me(db: Session = Depends(get_db)):
  """endpoint to get data of authenticated subscriber from db"""
  db_subscriber = repo.get_subscriber(db=db, subscriber_id=Auth(db).subscriber.id)
  if db_subscriber is None:
    raise HTTPException(status_code=404, detail="Subscriber not found")
  return db_subscriber


@app.put("/me", response_model=schemas.Subscriber)
def update_me(subscriber: dict, db: Session = Depends(get_db)):
  """endpoint to update an authenticated subscriber"""
  db_subscriber = repo.get_subscriber(db=db, subscriber_id=Auth(db).subscriber.id)
  if db_subscriber is None:
    raise HTTPException(status_code=404, detail="Subscriber not found")
  return repo.update_subscriber(db=db, subscriber=subscriber, subscriber_id=Auth(db).subscriber.id)


@app.get("/me/calendars", response_model=list[schemas.Calendar])
def read_my_calendars(db: Session = Depends(get_db)):
  """get all calendar connections of authenticated subscriber"""
  calendars = repo.get_calendars_by_subscriber(db, subscriber_id=Auth(db).subscriber.id)
  return calendars


@app.get("/me/appointments", response_model=list[schemas.Appointment])
def read_my_appointments(db: Session = Depends(get_db)):
  """get all appointments of authenticated subscriber"""
  appointments = repo.get_appointments_by_subscriber(db, subscriber_id=Auth(db).subscriber.id)
  return appointments


@app.post("/calendars", response_model=schemas.Calendar)
def create_my_calendar(calendar: schemas.CalendarBase, db: Session = Depends(get_db)):
  """endpoint to add a new calender connection for authenticated subscriber"""
  return repo.create_subscriber_calendar(db=db, calendar=calendar, subscriber_id=Auth(db).subscriber.id)


@app.get("/calendars/{id}", response_model=schemas.Calendar)
def read_calendar(id: int, db: Session = Depends(get_db)):
  """endpoint to get a calendar from db"""
  db_calendar = repo.get_calendar(db, calendar_id=id)
  if db_calendar is None:
    raise HTTPException(status_code=404, detail="Calendar not found")
  if not repo.calendar_is_owned(db, calendar_id=id, subscriber_id=Auth(db).subscriber.id):
    raise HTTPException(status_code=403, detail="Calendar not owned by subscriber")
  return db_calendar


@app.put("/calendars/{id}", response_model=schemas.Calendar)
def update_my_calendar(id: int, calendar: dict, db: Session = Depends(get_db)):
  """endpoint to add a new calender connection for authenticated subscriber"""
  db_calendar = repo.get_calendar(db, calendar_id=id)
  if db_calendar is None:
    raise HTTPException(status_code=404, detail="Calendar not found")
  if not repo.calendar_is_owned(db, calendar_id=id, subscriber_id=Auth(db).subscriber.id):
    raise HTTPException(status_code=403, detail="Calendar not owned by subscriber")
  return repo.update_subscriber_calendar(db=db, calendar=calendar, calendar_id=id)


@app.delete("/calendars/{id}", response_model=schemas.Calendar)
def delete_calendar(id: int, db: Session = Depends(get_db)):
  """endpoint to remove a calendar from db"""
  db_calendar = repo.get_calendar(db, calendar_id=id)
  if db_calendar is None:
    raise HTTPException(status_code=404, detail="Calendar not found")
  if not repo.calendar_is_owned(db, calendar_id=id, subscriber_id=Auth(db).subscriber.id):
    raise HTTPException(status_code=403, detail="Calendar not owned by subscriber")
  return repo.delete_subscriber_calendar(db=db, calendar_id=id)


@app.post("/appointments", response_model=schemas.Appointment)
def create_calendar_appointment(a_s: schemas.AppointmentSlots, db: Session = Depends(get_db)):
  """endpoint to add a new appointment with slots for a given calendar"""
  db_calendar = repo.get_calendar(db, calendar_id=a_s.appointment.calendar_id)
  if db_calendar is None:
    raise HTTPException(status_code=404, detail="Calendar not found")
  if not repo.calendar_is_owned(db, calendar_id=a_s.appointment.calendar_id, subscriber_id=Auth(db).subscriber.id):
    raise HTTPException(status_code=403, detail="Calendar not owned by subscriber")
  return repo.create_calendar_appointment(db=db, appointment=a_s.appointment, slots=a_s.slots)
