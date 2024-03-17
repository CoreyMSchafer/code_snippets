
class Employee:
    """A sample Employee class"""

    num_of_emps = 0
    raise_amt = 1.04

    class Employee:
    def __init__(self, first, last, annual_salary):
        self.first = first
        self.last = last
        self.annual_salary = annual_salary

    @property
    def email(self):
        return '{}.{}@HyperionDevBootCamp.com'.format(self.first, self.last).lower()

    def employee_details(self):
        return '{} {} £{}'.format(self.first, self.last, self.annual_salary)

    @property
    def fullname(self):
        return '{} {}'.format(self.first, self.last)

    def apply_raise(self):
        self.pay = int(self.pay * self.raise_amt)

    def __repr__(self):
        return "Employee('{}', '{}', {})".format(self.first, self.last, self.pay)


class Manager(Employee):
    """A sample Manager class"""

    def __init__(self, first, last, pay, employees=None):
        super().__init__(first, last, pay)
        self.employees = employees if employees else []

    def add_emp(self, emp):
        if emp not in self.employees:
            self.employees.append(emp)

    def remove_emp(self, emp):
        if emp in self.employees:
            self.employees.remove(emp)

    def __repr__(self):
        return "Manager('{}', '{}', {}, {})".format(self.first, self.last, self.pay, self.employees)
