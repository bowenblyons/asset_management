import requests

URL = "http://localhost:8000/"


def create_employee(first_name: str, last_name: str, email: str, eid: str) -> dict:
    url = f"{URL}employees"
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "eid": eid,
    }
    res = requests.post(url=url, json=payload)
    return res.json()

def get_employee_by_id(eid: str) -> dict:
    url = f"{URL}employees/{eid}"
    payload = {"eid": eid}
    res = requests.get(url=url, json=payload)
    return res.json()


if __name__ == "__main__":
    fname = "Bob"
    lname = "Thundren"
    email = "bthunder@test.com"
    eid = "bt1990"
    create_employee_res = create_employee(fname, lname, email, eid)
    get_employee_by_id_res = get_employee_by_id(eid)
    print(create_employee_res, get_employee_by_id_res)
