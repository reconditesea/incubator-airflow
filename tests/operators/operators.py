# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

import datetime
import os
import unittest
import six

from airflow import DAG, configuration, operators, utils
from airflow.utils.tests import skipUnlessImported
configuration.test_mode()

import os
import unittest


DEFAULT_DATE = datetime.datetime(2015, 1, 1)
DEFAULT_DATE_ISO = DEFAULT_DATE.isoformat()
DEFAULT_DATE_DS = DEFAULT_DATE_ISO[:10]
TEST_DAG_ID = 'unit_test_dag'


@skipUnlessImported('airflow.operators.mysql_operator', 'MySqlOperator')
class MySqlTest(unittest.TestCase):
    def setUp(self):
        configuration.test_mode()
        args = {
            'owner': 'airflow',
            'mysql_conn_id': 'airflow_db',
            'start_date': DEFAULT_DATE
        }
        dag = DAG(TEST_DAG_ID, default_args=args)
        self.dag = dag

    def mysql_operator_test(self):
        sql = """
        CREATE TABLE IF NOT EXISTS test_airflow (
            dummy VARCHAR(50)
        );
        """
        import airflow.operators.mysql_operator
        t = operators.mysql_operator.MySqlOperator(
            task_id='basic_mysql',
            sql=sql,
            mysql_conn_id='airflow_db',
            dag=self.dag)
        t.run(start_date=DEFAULT_DATE, end_date=DEFAULT_DATE, force=True)

    def mysql_operator_test_multi(self):
        sql = [
            "TRUNCATE TABLE test_airflow",
            "INSERT INTO test_airflow VALUES ('X')",
        ]
        import airflow.operators.mysql_operator
        t = operators.mysql_operator.MySqlOperator(
            task_id='mysql_operator_test_multi',
            mysql_conn_id='airflow_db',
            sql=sql, dag=self.dag)
        t.run(start_date=DEFAULT_DATE, end_date=DEFAULT_DATE, force=True)

    def test_mysql_to_mysql(self):
        sql = "SELECT * FROM INFORMATION_SCHEMA.TABLES LIMIT 100;"
        import airflow.operators.generic_transfer
        t = operators.generic_transfer.GenericTransfer(
            task_id='test_m2m',
            preoperator=[
                "DROP TABLE IF EXISTS test_mysql_to_mysql",
                "CREATE TABLE IF NOT EXISTS "
                "test_mysql_to_mysql LIKE INFORMATION_SCHEMA.TABLES"
            ],
            source_conn_id='airflow_db',
            destination_conn_id='airflow_db',
            destination_table="test_mysql_to_mysql",
            sql=sql,
            dag=self.dag)
        t.run(start_date=DEFAULT_DATE, end_date=DEFAULT_DATE, force=True)

    def test_sql_sensor(self):
        t = operators.sensors.SqlSensor(
            task_id='sql_sensor_check',
            conn_id='mysql_default',
            sql="SELECT count(1) FROM INFORMATION_SCHEMA.TABLES",
            dag=self.dag)
        t.run(start_date=DEFAULT_DATE, end_date=DEFAULT_DATE, force=True)

@skipUnlessImported('airflow.operators.postgres_operator', 'PostgresOperator')
class PostgresTest(unittest.TestCase):
    def setUp(self):
        configuration.test_mode()
        args = {'owner': 'airflow', 'start_date': DEFAULT_DATE}
        dag = DAG(TEST_DAG_ID, default_args=args)
        self.dag = dag

    def postgres_operator_test(self):
        sql = """
        CREATE TABLE IF NOT EXISTS test_airflow (
            dummy VARCHAR(50)
        );
        """
        import airflow.operators.postgres_operator
        t = operators.postgres_operator.PostgresOperator(
            task_id='basic_postgres', sql=sql, dag=self.dag)
        t.run(start_date=DEFAULT_DATE, end_date=DEFAULT_DATE, force=True)

        autocommitTask = operators.postgres_operator.PostgresOperator(
            task_id='basic_postgres_with_autocommit',
            sql=sql,
            dag=self.dag,
            autocommit=True)
        autocommitTask.run(
            start_date=DEFAULT_DATE,
            end_date=DEFAULT_DATE,
            force=True)


@skipUnlessImported('airflow.operators.hive_operator', 'HiveOperator')
@skipUnlessImported('airflow.operators.postgres_operator', 'PostgresOperator')
class TransferTests(unittest.TestCase):
    cluster = None

    def setUp(self):
        configuration.test_mode()
        args = {'owner': 'airflow', 'start_date': DEFAULT_DATE_ISO}
        dag = DAG(TEST_DAG_ID, default_args=args)
        self.dag = dag

    def test_clear(self):
        self.dag.clear(
            start_date=DEFAULT_DATE,
            end_date=datetime.datetime.now())

    def test_mysql_to_hive(self):
        # import airflow.operators
        from airflow.operators.mysql_to_hive import MySqlToHiveTransfer
        sql = "SELECT * FROM baby_names LIMIT 1000;"
        t = MySqlToHiveTransfer(
            task_id='test_m2h',
            mysql_conn_id='airflow_ci',
            hive_cli_conn_id='beeline_default',
            sql=sql,
            hive_table='test_mysql_to_hive',
            recreate=True,
            delimiter=",",
            dag=self.dag)
        t.run(start_date=DEFAULT_DATE, end_date=DEFAULT_DATE, force=True)

    def test_mysql_to_hive_partition(self):
        from airflow.operators.mysql_to_hive import MySqlToHiveTransfer
        sql = "SELECT * FROM baby_names LIMIT 1000;"
        t = MySqlToHiveTransfer(
            task_id='test_m2h',
            mysql_conn_id='airflow_ci',
            hive_cli_conn_id='beeline_default',
            sql=sql,
            hive_table='test_mysql_to_hive_part',
            partition={'ds': DEFAULT_DATE_DS},
            recreate=False,
            create=True,
            delimiter=",",
            dag=self.dag)
        t.run(start_date=DEFAULT_DATE, end_date=DEFAULT_DATE, force=True)
