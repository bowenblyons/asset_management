from contextlib import contextmanager
from datetime import datetime
import json
import os
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
import psycopg
from psycopg import sql
from pydantic import BaseModel, ConfigDict, Field, model_validator


app = FastAPI(title="Asset Management API")


def get_dsn() -> str:
    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    dbname = os.environ["DB_NAME"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    return (
        f"host={host} port={port} dbname={dbname} " f"user={user} password={password}"
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
    created: datetime


# geometry in classes for line or point
class PointGeometryIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class LineGeometryIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    linestring: list[tuple[float, float]] = Field(
        min_length=2, description="List of [lon,lat] pairs"
    )

    @model_validator(mode="after")
    def validate_coordinates(self) -> "LineGeometryIn":
        for lon, lat in self.linestring:
            if not (-180 <= lon <= 180):
                raise ValueError(f"bad longitude: {lon}")
            if not (-90 <= lat <= 90):
                raise ValueError(f"bad latitude: {lat}")
        return self


# id, type, description, estimated value, geom_point, geom_line
class AssetsCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asset_type: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=200)
    estimated_value: int = Field(default=0, ge=0)
    geometry_type: Literal["point", "line"]
    point: Optional[PointGeometryIn] = None
    line: Optional[LineGeometryIn] = None

    @model_validator(mode="after")
    def validate_geometry(self) -> "AssetsCreate":
        if self.geometry_type == "point":
            if self.point is None or self.line is not None:
                raise ValueError(
                    "Point asset must include point and no line coodinates"
                )
        elif self.geometry_type == "line":
            if self.line is None or self.point is not None:
                raise ValueError(
                    "Line asset must include line and no point coordinates"
                )
        return self


# geometry out classes for line and point
class PointGeometryOut(BaseModel):
    type: Literal["point"] = "point"
    lat: float
    lon: float


class LineGeometryOut(BaseModel):
    type: Literal["line"] = "line"
    linestring: list[tuple[float, float]]


class AssetsOut(BaseModel):
    id: int
    asset_type: str
    description: str
    estimated_value: int
    geometry: PointGeometryOut | LineGeometryOut
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
    result: Literal["pass", "review", "fail"] = Field()
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


def getGeo(row: str) -> PointGeometryOut | LineGeometryOut:
    geo = json.loads(row)
    if geo.get("type") == "LineString":
        geo = LineGeometryOut(type="line", linestring=geo.get("coordinates"))
    elif geo.get("type") == "Point":
        geo = PointGeometryOut(
            type="point", lon=geo.get("coordinates")[0], lat=geo.get("coordinates")[1]
        )
    return geo


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


# employees
@app.post("/employees", response_model=EmployeesOut, status_code=201)
def create_employee(payload: EmployeesCreate) -> EmployeesOut:
    """Add an employee"""

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                "INSERT INTO {table} ({fields}) VALUES ({values}) RETURNING {return_fields}"
            ).format(
                table=sql.Identifier("employees"),
                fields=sql.SQL(",").join(
                    [sql.Identifier("first_name"), sql.Identifier("last_name")]
                ),
                values=sql.SQL(",").join([payload.first_name, payload.last_name]),
                return_fields=sql.SQL(",").join(
                    [
                        sql.Identifier("id"),
                        sql.Identifier("first_name"),
                        sql.Identifier("last_name"),
                        sql.Identifier("deleted_at"),
                        sql.Identifier("created"),
                    ]
                ),
            ),
            payload.model_dump(),
        )
        row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create employee")

    return EmployeesOut(
        id=row[0],
        first_name=row[1],
        last_name=row[2],
        deleted_at=row[3],
        created=row[4],
    )


@app.get("/employees/{employee_id}", response_model=EmployeesOut, status_code=201)
def get_employee_by_id(employee_id: int) -> EmployeesOut:
    """Get an employee by id"""

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            sql.SQL("SELECT {fields} FROM {table} WHERE id={eid}").format(
                fields=sql.SQL(",").join(
                    [
                        sql.Identifier("id"),
                        sql.Identifier("first_name"),
                        sql.Identifier("last_name"),
                        sql.Identifier("deleted_at"),
                        sql.Identifier("created"),
                    ]
                ),
                table=sql.Identifier("employees"),
                eid=employee_id,
            )
        )
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to get employee")

    return EmployeesOut(
        id=row[0],
        first_name=row[1],
        last_name=row[2],
        deleted_at=row[3],
        created=row[4],
    )


@app.get("/employees", response_model=list[EmployeesOut])
def get_employee_list() -> list[EmployeesOut]:
    """List all employees"""

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            sql.SQL("SELECT {fields} FROM {table} ORDER BY {order_col}").format(
                fields=sql.SQL(",").join(
                    [
                        sql.Identifier("id"),
                        sql.Identifier("first_name"),
                        sql.Identifier("last_name"),
                        sql.Identifier("deleted_at"),
                        sql.Identifier("created"),
                    ]
                ),
                table=sql.Identifier("employees"),
                order_col=sql.Identifier("last_name"),
            )
        )
        rows = cur.fetchall()

    return [
        EmployeesOut(
            id=row[0],
            first_name=row[1],
            last_name=row[2],
            deleted_at=row[3],
            created=row[4],
        )
        for row in rows
    ]


# assets
@app.post("/assets", response_model=AssetsOut, status_code=201)
def create_asset(payload: AssetsCreate) -> AssetsOut:
    """Add an asset entry"""

    if payload.geometry_type == "point" and payload.point:
        query = """
            INSERT INTO assets (
                asset_type,
                description,
                estimated_value,
                geom
            )
            VALUES (
                %s,
                %s,
                %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            )
            RETURNING
                id,
                asset_type,
                description,
                estimated_value,
                ST_AsGeoJSON(geom),
                deleted_at,
                created
        """
        params = (
            payload.asset_type,
            payload.description,
            payload.estimated_value,
            payload.point.lon,
            payload.point.lat,
        )

    elif payload.geometry_type == "line" and payload.line:
        wkt = (
            "LINESTRING("
            + ", ".join(f"{lon} {lat}" for lon, lat in payload.line.linestring)
            + ")"
        )

        query = """
            INSERT INTO assets (
                asset_type,
                description,
                estimated_value,
                geom
            )
            VALUES (
                %s,
                %s,
                %s,
                ST_GeomFromText(%s, 4326)
            )
            RETURNING
                id,
                asset_type,
                description,
                estimated_value,
                ST_AsGeoJSON(geom),
                deleted_at,
                created
        """
        params = (
            payload.asset_type,
            payload.description,
            payload.estimated_value,
            wkt,
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid geometry")

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create asset")

    geo = getGeo(row[4])

    return AssetsOut(
        id=row[0],
        asset_type=row[1],
        description=row[2],
        estimated_value=row[3],
        geometry=geo,
        deleted_at=row[5],
        created_at=row[6],
    )


@app.get("/assets/{asset_id}", response_model=AssetsOut)
def get_asset_by_id(asset_id: int) -> AssetsOut:
    """Get a single asset by ID"""
    query = """
        SELECT id, asset_type, description, estimated_value, ST_AsGeoJSON(geom) AS geom, deleted_at, created
        FROM assets WHERE id=%s;
    """
    params = (asset_id,)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(query=query, params=params)
        row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to get asset")

    geo = getGeo(row[4])

    return AssetsOut(
        id=row[0],
        asset_type=row[1],
        description=row[2],
        estimated_value=row[3],
        geometry=geo,
        deleted_at=row[5],
        created_at=row[6],
    )


@app.get("/assets", response_model=list[AssetsOut])
def get_asset_list() -> list[AssetsOut]:
    """List all assets"""
    sql = """
        SELECT id, asset_type, description, estimated_value, ST_AsGeoJSON(geom) AS geom, deleted_at, created
        FROM assets ORDER BY id;
    """

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    return [
        AssetsOut(
            id=row[0],
            asset_type=row[1],
            description=row[2],
            estimated_value=row[3],
            geometry=getGeo(row[4]),
            deleted_at=row[5],
            created_at=row[6],
        )
        for row in rows
    ]


# issues
@app.post("/issues", response_model=IssuesOut, status_code=201)
def create_issue(payload: IssuesCreate) -> IssuesOut:
    """Add an issue entry"""

    query = """
        INSERT INTO issues (
            issue_type, priority, status, asset_id, description, estimated_cost, reported_by
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s
        ) RETURNING
            id, issue_type, priority, status, asset_id, description, estimated_cost, reported_by, deleted_at, created;
    """
    params = (
        payload.issue_type,
        payload.priority,
        payload.status,
        payload.asset_id,
        payload.description,
        payload.estimated_cost,
        payload.reported_by,
    )
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create asset")

    return IssuesOut(
        id=row[0],
        issue_type=row[1],
        priority=row[2],
        status=row[3],
        asset_id=row[4],
        description=row[5],
        estimated_cost=row[6],
        reported_by=row[7],
        deleted_at=row[8],
        created_at=row[9],
    )


@app.get("/issues/{issue_id}", response_model=IssuesOut)
def get_issue_by_id(issue_id: int) -> IssuesOut:
    """Get a single issue by ID"""
    q = """
        SELECT id, issue_type, priority, status, asset_id, description, estimated_cost, reported_by, deleted_at, created
        FROM issues WHERE id=%s;
    """
    p = (issue_id,)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(q, p)
        row = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to find issue")

    return IssuesOut(
        id=row[0],
        issue_type=row[1],
        priority=row[2],
        status=row[3],
        asset_id=row[4],
        description=row[5],
        estimated_cost=row[6],
        reported_by=row[7],
        deleted_at=row[8],
        created_at=row[9],
    )


@app.get("/issues", response_model=list[IssuesOut])
def get_issue_list() -> list[IssuesOut]:
    """Get a list of issues"""
    sql = """
        SELECT id, issue_type, priority, status, asset_id, description, estimated_cost, reported_by, deleted_at, created
        FROM issues ORDER BY id;
    """

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    return [
        IssuesOut(
            id=row[0],
            issue_type=row[1],
            priority=row[2],
            status=row[3],
            asset_id=row[4],
            description=row[5],
            estimated_cost=row[6],
            reported_by=row[7],
            deleted_at=row[8],
            created_at=row[9],
        )
        for row in rows
    ]


@app.patch("/issues/{issue_id}", response_model=IssuesOut)
def update_issue(issue_id: int, payload: IssuesUpdate) -> IssuesOut:

    if payload.priority is None or payload.status is None:
        raise HTTPException(status_code=500, detail="Must provide both status and priority for update for now")

    query = """
        UPDATE issues SET priority=%s, status=%s WHERE id = %s
        RETURNING id, issue_type, priority, status, asset_id, 
        description, estimated_cost, reported_by, deleted_at, created;
    """

    params = (payload.priority, payload.status, issue_id,)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=404, detail="No such issue found")

    return IssuesOut(
        id=row[0],
        issue_type=row[1],
        priority=row[2],
        status=row[3],
        asset_id=row[4],
        description=row[5],
        estimated_cost=row[6],
        reported_by=row[7],
        deleted_at=row[8],
        created_at=row[9],
    )


@app.post("/tickets", response_model=TicketsOut, status_code=201)
def create_ticket(payload: TicketsCreate) -> TicketsOut:
    q = """
        INSERT INTO tickets (
            issue_id, work_description, employee_id, completed_at, asset_id
        ) VALUES (
            %s, %s, %s, %s, %s
        ) RETURNING
            id, issue_id, work_description, employee_id, completed_at, asset_id, deleted_at, created;
    """

    p = (payload.issue_id, payload.work_description, payload.employee_id, payload.completed_at, payload.asset_id,)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(q, p)
        row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=500, detail="Create ticket failed.")

    return TicketsOut (
        id=row[0], issue_id=row[1], work_description=row[2], employee_id=row[3], completed_at=row[4],
        asset_id=row[5], deleted_at=row[6], created_at=row[7]
    )

@app.get("/tickets/{ticket_id}", response_model=TicketsOut)
def get_ticket_by_id(ticket_id: int) -> TicketsOut:
    q = """
        SELECT id, issue_id, work_description, employee_id, completed_at, asset_id, deleted_at, created
        FROM tickets WHERE id = %s;
    """

    p = (ticket_id, )

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(q, p)
        row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=500, detail="GET ticket failed.")

    return TicketsOut (
        id=row[0], issue_id=row[1], work_description=row[2], employee_id=row[3], completed_at=row[4],
        asset_id=row[5], deleted_at=row[6], created_at=row[7]
    )

@app.get("/tickets", response_model=list[TicketsOut])
def get_ticket_list() -> list[TicketsOut]:
    q = """
        SELECT id, issue_id, work_description, employee_id, completed_at, asset_id, deleted_at, created
        FROM tickets ORDER BY id;
    """

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(q)
        rows = cur.fetchall()
        conn.commit()

    return [ 
        TicketsOut (
            id=row[0], issue_id=row[1], work_description=row[2], employee_id=row[3], completed_at=row[4],
            asset_id=row[5], deleted_at=row[6], created_at=row[7]
        ) for row in rows
    ]

@app.post("/inspections", response_model=InspectionsOut)
def create_inspection(payload: InspectionsCreate) -> InspectionsOut:
    q = """
        INSERT INTO inspections (
            asset_id, result, description, completed_at, employee_id
        ) VALUES (
            %s, %s, %s, %s, %s
        ) RETURNING
            id, asset_id, result, description, completed_at, employee_id, deleted_at, created;
    """

    p = (payload.asset_id, payload.result, payload.description, payload.completed_at, payload.employee_id,)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(q, p)
        row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=500, detail="inspection creation failed. ")

    return InspectionsOut (
        id=row[0], asset_id=row[1], result=row[2], description=row[3], completed_at=row[4],
        employee_id=row[5], deleted_at=row[6], created_at=row[7]
    )

@app.get("/inspections/{inspection_id}", response_model=InspectionsOut)
def get_inspection_by_id(inspection_id: int) -> InspectionsOut:
    q = """
        SELECT
            id, asset_id, result, description, completed_at, employee_id, deleted_at, created
        FROM inspections WHERE id = %s;
    """

    p = (inspection_id,)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(q, p)
        row = cur.fetchone()
        conn.commit()

    if row is None:
        raise HTTPException(status_code=404, detail="inspection get failed. ")

    return InspectionsOut (
        id=row[0], asset_id=row[1], result=row[2], description=row[3], completed_at=row[4],
        employee_id=row[5], deleted_at=row[6], created_at=row[7]
    )

@app.get("/inspections", response_model=list[InspectionsOut])
def get_inspection_list() -> list[InspectionsOut]:
    sql = """
        SELECT
            id, asset_id, result, description, completed_at, employee_id, deleted_at, created
        FROM inspections ORDER BY id;
    """

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        conn.commit()

    return [
        InspectionsOut (
            id=row[0], asset_id=row[1], result=row[2], description=row[3], completed_at=row[4],
            employee_id=row[5], deleted_at=row[6], created_at=row[7]
        )
        for row in rows
    ]
