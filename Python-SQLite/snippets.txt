
def insert_emp(emp):
    pass


def get_emps_by_name(lastname):
    pass


def update_pay(emp, pay):
    pass


def remove_emp(emp):
    pass




def update_pay(emp, pay):
    with conn:
        c.execute("""UPDATE employees SET pay = :pay
                    WHERE first = :first AND last = :last""",
                  {'first': emp.first, 'last': emp.last, 'pay': pay})


def remove_emp(emp):
    with conn:
        c.execute("DELETE from employees WHERE first = :first AND last = :last",
                  {'first': emp.first, 'last': emp.last})
