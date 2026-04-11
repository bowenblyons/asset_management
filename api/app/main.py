
from contextlib import contextmanager
from datetime import datetime
import os
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
import psycopg
from pydantic import BaseModel, ConfigDict, Field


app = FastAPI(title="Asset Management API")

def get_dsn() -> str:
    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    dbname = os.environ["DB_NAME"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    return (
        f"host={host} port={port} dbname={dbname} "
        f"user={user} password={password}"
    )

@contextmanager
def get_conn():
    conn = psycopg.connect(get_dsn())
    try:
        yield conn
    finally:
        conn.close()

class HealthResponse(BaseModel):
    status: str

# id, first name, last name
class EmployeesCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)

class EmployeesOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    deleted_at: Optional[datetime]
    created_at: datetime

# id, type, description, estimated value, geom_point, geom_line
class AssetsCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asset_type: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=200)
    estimated_value: int = Field(default=0)
    # geom_point, geom_line?

class AssetsOut(BaseModel):
    id: int
    asset_type: str
    description: str
    estimated_value: int
    # geom_point, geom_line?
    deleted_at: Optional[datetime]
    created_at: datetime

# id, type, priority, status, asset_id, description, estimated cost, reported by
class IssuesCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    issue_type: str = Field(min_length=1, max_length=50)
    priority: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    status: Literal["open", "closed"] = "open"
    asset_id: int = Field()
    description: str = Field(min_length=1, max_length=200)
    estimated_cost: int = Field()
    reported_by: int = Field()

class IssuesUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    priority: Optional[Literal["low", "medium", "high", "critical"]] = None
    status: Optional[Literal["open", "closed"]] = None

class IssuesOut(BaseModel):
    id: int
    issue_type: str
    priority: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "closed"]
    asset_id: int
    description: str
    estimated_cost: int
    reported_by: int
    deleted_at: Optional[datetime]
    created_at: datetime

# id, issue_id, work_description, employee_id, completed_at, asset_id
class TicketsCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    issue_id: int = Field()
    work_description: str = Field(min_length=1, max_length=200)
    employee_id: int = Field()
    completed_at: datetime = Field(default=datetime.now())
    asset_id: Optional[int] = Field(default=None)

class TicketsOut(BaseModel):
    id: int
    issue_id: int
    work_description: str
    employee_id: int
    completed_at: datetime
    asset_id: Optional[int]
    deleted_at: Optional[datetime]
    created_at: datetime

# id, asset_id, result, description, completed_at, employee_id
class InspectionsCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asset_id: int = Field()
    result: str = Literal["pass", "review", "fail"]
    description: str = Field(min_length=1, max_length=200)
    completed_at: datetime = Field(default=datetime.now())
    employee_id: int = Field()

class InspectionsOut(BaseModel):
    id: int
    asset_id: int
    result: str
    description: str
    completed_at: datetime
    employee_id: int
    deleted_at: Optional[datetime]
    created_at: datetime

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")

# employees
@app.post("/employees", response_model=EmployeesOut, status_code=201)
def create_employee(payload: EmployeesCreate) -> EmployeesOut:
    """Add an employee"""
    sql = """
        INSERT INTO employees (
            first_name, last_name
        ) VALUES (
            %(first_name)s, %(last_name)s
        ) RETURNING
            id, first_name, last_name, deleted_at, created;
    """

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, payload.model_dump())
        row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create employee")
    
    return EmployeesOut(
        first_name=row[0], last_name=row[1]
    )

@app.get("/employees", response_model=EmployeesOut, status_code=201)
def get_employee_by_id() -> EmployeesOut:
    """Get an employee by id"""
    sql = """
        SELECT first_name, last_name FROM employee
        WHERE id=%(employee_id)s;
    """

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to get employee")
    
    return EmployeesOut(
        first_name=row[0], last_name=row[1]
    )

@app.get("/employees", response_model=list[EmployeesOut])
def get_employee_list() -> list[EmployeesOut]:
    """List all employees"""
    sql = """
        SELECT id, first_name, last_name
        FROM assets ORDER BY id;
    """

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    return [
        EmployeesOut(
            id = row[0], first_name=row[1], last_name=row[2]
        )
        for row in rows
    ]

# # assets
# @app.post("/assets", response_model=AssetsOut, status_code=201)
# def create_asset(payload: AssetsCreate) -> AssetsOut:
#     """Add an asset entry"""

#     sql = """
#         INSERT INTO assets (
#             asset_type, description, estimated_value
#         ) VALUES (
#             %(asset_type)s, %(description)s, %(estimated_value)s
#         ) RETURNING
#             id, asset_type, description, estimated_value;
#     """
#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql, payload.model_dump())
#         row = cur.fetchone()
#         conn.commit()
    
#     if row is None:
#         raise HTTPException(status_code=500, detail="Failed to create asset")
    
#     return AssetsOut(
#         id = row[0], asset_type=row[1], description=row[2], estimated_value=row[3]
#     )

# @app.get("/assets", response_model=AssetsOut)
# def get_asset_by_id(asset_id: int) -> AssetsOut:
#     """Get a single asset by ID"""
#     sql = """
#         SELECT id, asset_type, description, estimated_value
#         FROM assets WHERE id=%(asset_id)s;
#     """

#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql)
#         row = cur.fetchall()

#     return AssetsOut(
#         id = row[0], asset_type=row[1], description=row[2], estimated_value=row[3]
#     )

# @app.get("/assets", response_model=list[AssetsOut])
# def get_asset_list() -> list[AssetsOut]:
#     """List all assets"""
#     sql = """
#         SELECT id, asset_type, description, estimated_value
#         FROM assets ORDER BY id;
#     """

#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql)
#         rows = cur.fetchall()

#     return [
#         AssetsOut(
#             id = row[0], asset_type=row[1], description=row[2], estimated_value=row[3]
#         )
#         for row in rows
#     ]

# # issues
# @app.post("/issues", response_model=IssuesOut, status_code=201)
# def create_issue(payload: IssuesCreate) -> IssuesOut:
#     """Add an issue entry"""

#     sql = """
#         INSERT INTO issues (
#             issue_type, priority, status, asset_id, description, estimated_cost, reported_by
#         ) VALUES (
#             %(issue_type)s, %(priority)s, %(status)s, %(asset_id)s, %(description)s, %(estimated_cost)s, %(reported_by)s
#         ) RETURNING
#             id, issue_type, priority, status, asset_id, description, estimated_cost, reported_by;
#     """
#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql, payload.model_dump())
#         row = cur.fetchone()
#         conn.commit()
    
#     if row is None:
#         raise HTTPException(status_code=500, detail="Failed to create asset")
    
#     return IssuesOut(
#         id = row[0], issue_type=row[1], priority=row[3], status=row[4], asset_id=row[5], description=row[6], estimated_cost=row[7], reported_by=row[8]
#     )

# @app.get("/issues", response_model=IssuesOut)
# def get_issue_by_id(issue_id: int) -> IssuesOut:
#     """Get a single issue by ID"""
#     sql = """
#         SELECT id, issue_type, priority, status, asset_id, description, estimated_cost, reported_by
#         FROM issues WHERE id=%(issue_id)s;
#     """

#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql)
#         row = cur.fetchall()

#     return IssuesOut(
#         id = row[0], issue_type=row[1], priority=row[3], status=row[4], asset_id=row[5], description=row[6], estimated_cost=row[7], reported_by=row[8]
#     )

# @app.get("/issues", response_model=list(IssuesOut))
# def get_issue_list(issue_id: int) -> list[IssuesOut]:
#     """Get a list of issues"""
#     sql = """
#         SELECT id, issue_type, priority, status, asset_id, description, estimated_cost, reported_by
#         FROM issues ORDER BY id;
#     """

#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql)
#         rows = cur.fetchall()

#     return [
#         IssuesOut(
#             id = row[0], issue_type=row[1], priority=row[3], status=row[4], asset_id=row[5], description=row[6], estimated_cost=row[7], reported_by=row[8]
#         ) 
#         for row in rows
#     ]

# @app.patch("/issues/{issue_id}", response_model=IssuesOut)
# def update_issue(issue_id: int, payload: IssuesUpdate) -> IssuesOut:
#     updates = payload.model_dump(exclude_unset=True)

#     if not updates:
#         raise HTTPException(status_code=400, detail="No fields for update")
    
#     set_clauses: list[str] = []
#     params: dict[str, object] = {"issue_id": issue_id}

#     for key, val in updates.items():
#         set_clauses.append(f"{key} = %({key})s")
#         params[key] = val

#     sql = f"""
#         UPDATE issues SET {", ".join(set_clauses)} WHERE id = %(ticket_id)s
#         RETURNING 
#         id, issue_type, priority, status, asset_id, description, estimated_cost, reported_by;
#     """

#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql, params)
#         row = cur.fetchone()
#         conn.commit()

#     if row is None:
#         raise HTTPException(status_code=404, detail="No such issue found")
    
#     return IssuesOut (
#         id = row[0], issue_type=row[1], priority=row[2], status=row[3], asset_id=row[4],
#         description=row[5], estimated_cost=row[6], reported_by=row[7]
#     )

# @app.post("/tickets", response_model=TicketsOut, status_code=201)
# def create_ticket(payload: TicketsCreate) -> TicketsOut:
#     sql = """
#         INSERT INTO tickets (
#             issue_id, work_description, employee_id, completed_at, asset_id
#         ) VALUES (
#             %(issue_id)s, %(work_description)s, %(employee_id)s, %(completed_at)s, %(asset_id)s
#         ) RETURNING
#             id, issue_id, work_description, employee_id, complete_at, asset_id;
#     """

#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql, payload.model_dump())
#         row = cur.fetchone()
#         conn.commit()

#     if row is None:
#         raise HTTPException(status_code=500, detail="Create ticket failed.")
    
#     return TicketsOut (
#         id=row[0], issue_id=row[1], work_description=row[2], employee_id=row[3], completed_at=row[4],
#         asset_id=row[5]
#     )

# @app.get("/tickets", response_model=TicketsOut)
# def get_ticket_by_id(ticket_id: int) -> TicketsOut:
#     sql = """
#         SELECT issue_id, work_description, employee_id, completed_at, asset_id
#         FROM tickets WHERE id = %(ticket_id)s;
#     """

#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql)
#         row = cur.fetchone()
#         conn.commit()

#     if row is None:
#         raise HTTPException(status_code=500, detail="Create ticket failed.")
    
#     return TicketsOut (
#         id=row[0], issue_id=row[1], work_description=row[2], employee_id=row[3], completed_at=row[4],
#         asset_id=row[5]
#     )

# @app.get("/tickets", response_model=list(TicketsOut))
# def get_ticket_list() -> list[TicketsOut]:
#     sql = """
#         SELECT issue_id, work_description, employee_id, completed_at, asset_id
#         FROM tickets ORDER BY id;
#     """

#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql)
#         rows = cur.fetchall()
#         conn.commit()

#     if rows is None:
#         raise HTTPException(status_code=500, detail="Create ticket failed.")
    
#     return [
#         TicketsOut (
#             id=row[0], issue_id=row[1], work_description=row[2], employee_id=row[3], 
#             completed_at=row[4], asset_id=row[5]
#         )
#         for row in rows
#     ]

# @app.post("/inspections", response_model=InspectionsOut)
# def create_inspection(payload: InspectionsCreate) -> InspectionsOut:
#     sql = """
#         INSERT INTO inspections (
#             asset_id, result, description, completed_at, employee_id
#         ) VALUES (
#             %(asset_id)s, %(result)s, %(description)s, %(completed_at)s, %(employee_id)s
#         ) RETURNING
#             id, asset_id, result, description, completed_at, employee_id;
#     """

#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql, payload.model_dump())
#         row = cur.fetchone()
#         conn.commit()

#     if row is None:
#         raise HTTPException(status_code=500, detail="inspection creation failed. ")
    
#     return InspectionsOut (
#         id=row[0], asset_id=row[1], result=row[2], description=row[3], completed_at=row[4],
#         employee_id=row[5]
#     )

# @app.get("/inspections", response_model=InspectionsOut)
# def get_inspection_by_id(inspection_id: int) -> InspectionsOut:
#     sql = """
#         SELECT
#             id, asset_id, result, description, completed_at, employee_id
#         FROM inspections WHERE id = $(inspection_id)s;
#     """

#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql)
#         row = cur.fetchone()

#     if row is None:
#         raise HTTPException(status_code=404, detail="inspection get failed. ")
    
#     return InspectionsOut (
#         id=row[0], asset_id=row[1], result=row[2], description=row[3], completed_at=row[4],
#         employee_id=row[5]
#     )

# @app.get("/inspections", response_model=list(InspectionsOut))
# def get_inspection_list() -> list[InspectionsOut]:
#     sql = """
#         SELECT
#             id, asset_id, result, description, completed_at, employee_id
#         FROM inspections ORDER BY id;
#     """

#     with get_conn() as conn, conn.cursor() as cur:
#         cur.execute(sql)
#         rows = cur.fetchall()

#     if rows is None:
#         raise HTTPException(status_code=404, detail="inspection get failed. ")
    
#     return [ 
#         InspectionsOut (
#             id=row[0], asset_id=row[1], result=row[2], description=row[3], completed_at=row[4],
#             employee_id=row[5]
#         )
#         for row in rows
#     ]