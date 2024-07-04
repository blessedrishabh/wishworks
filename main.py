from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import databases
import sqlalchemy

DATABASE_URL = "postgresql://property_db_hpz4_user:0kjonSYQfnKoLkJLJrKtrMiWmSoZdpPS@dpg-cq3a8kcs1f4s73fc9rqg-a.oregon-postgres.render.com/property_db_hpz4"

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

localities = sqlalchemy.Table(
    "localities",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, unique=True),
)

properties = sqlalchemy.Table(
    "properties",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("locality_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("localities.id")),
    sqlalchemy.Column("owner_name", sqlalchemy.String),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now()),
    sqlalchemy.Column("updated_at", sqlalchemy.DateTime, server_default=sqlalchemy.func.now(), onupdate=sqlalchemy.func.now()),
)

app = FastAPI(
    title="Real Estate Project",
    description="Simple CRUD API",
    docs_url="/"
)

class PropertyCreate(BaseModel):
    property_name: str
    locality: str
    owner_name: str

class PropertyUpdate(BaseModel):
    property_id: int
    locality_id: int
    owner_name: str

class PropertyResponse(BaseModel):
    property_id: int
    property_name: str
    owner_name: str

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/properties/", response_model=dict)
async def add_new_property(property: PropertyCreate):
    query = localities.select().where(localities.c.name == property.locality)
    locality = await database.fetch_one(query)
    
    if not locality:
        locality_id = await database.execute(localities.insert().values(name=property.locality))
    else:
        locality_id = locality['id']
    
    query = properties.insert().values(
        name=property.property_name,
        locality_id=locality_id,
        owner_name=property.owner_name
    )
    property_id = await database.execute(query)
    
    return {"message": "Property added successfully", "property_id": property_id}

@app.get("/properties/", response_model=List[PropertyResponse])
async def fetch_all_properties(locality: str = None, locality_id: int = None):
    if locality:
        query = properties.select().join(localities).where(localities.c.name == locality)
    elif locality_id:
        query = properties.select().where(properties.c.locality_id == locality_id)
    else:
        raise HTTPException(status_code=400, detail="Please provide either locality or locality_id")
    
    results = await database.fetch_all(query)
    return [PropertyResponse(property_id=row['id'], property_name=row['name'], owner_name=row['owner_name']) for row in results]

@app.put("/properties/", response_model=dict)
async def update_property_details(property: PropertyUpdate):
    query = properties.update().where(properties.c.id == property.property_id).values(
        locality_id=property.locality_id,
        owner_name=property.owner_name
    )
    await database.execute(query)
    
    query = properties.select().where(properties.c.id == property.property_id)
    updated_property = await database.fetch_one(query)
    
    return {
        "message": "Property updated successfully",
        "property_id": updated_property['id'],
        "property_name": updated_property['name'],
        "locality_id": updated_property['locality_id'],
        "owner_name": updated_property['owner_name']
    }

@app.delete("/properties/{property_id}", response_model=dict)
async def delete_property_record(property_id: int):
    query = properties.delete().where(properties.c.id == property_id)
    await database.execute(query)
    return {"message": "Property deleted successfully"}

# Additional API: Search properties by owner name
@app.get("/properties/search/", response_model=List[PropertyResponse])
async def search_properties_by_owner(owner_name: str):
    query = properties.select().where(properties.c.owner_name.ilike(f"%{owner_name}%"))
    results = await database.fetch_all(query)
    return [PropertyResponse(property_id=row['id'], property_name=row['name'], owner_name=row['owner_name']) for row in results]