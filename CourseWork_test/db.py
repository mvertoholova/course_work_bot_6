import mysql.connector

def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="209MVertoholovaAdmin",
        password="punpun..Baki8Na594/",
        database="schedule_chmnu_course_test"
    )
    return connection

def get_connection_group():
    connection_group = mysql.connector.connect(
        host="localhost",
        user="209MVertoholovaAdmin",
        password="punpun..Baki8Na594/",
        database="schedule_bot"
    )
    return connection_group