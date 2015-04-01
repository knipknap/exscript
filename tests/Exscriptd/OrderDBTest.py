import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tempfile          import NamedTemporaryFile
from getpass           import getuser
from sqlalchemy        import create_engine
from Exscriptd.Order   import Order
from Exscriptd.Task    import Task
from Exscriptd.OrderDB import OrderDB

def testfunc(foo):
    pass

class OrderDBTest(unittest.TestCase):
    CORRELATE = OrderDB

    def setUp(self):
        from sqlalchemy.pool import NullPool
        self.dbfile = NamedTemporaryFile()
        self.engine = create_engine('sqlite:///' + self.dbfile.name,
                                    poolclass = NullPool)
        self.db     = OrderDB(self.engine)

    def tearDown(self):
        self.dbfile.close()

    def testConstructor(self):
        db = OrderDB(self.engine)

    def testInstall(self):
        self.db.install()

    def testUninstall(self):
        self.testInstall()
        self.db.uninstall()
        self.db.install()

    def testClearDatabase(self):
        self.testAddOrder()
        self.db.clear_database()

        orders = self.db.get_orders()
        self.assertTrue(len(orders) == 0)

    def testDebug(self):
        self.assertTrue(not self.engine.echo)
        self.db.debug()
        self.assertTrue(self.engine.echo)
        self.db.debug(False)
        self.assertTrue(not self.engine.echo)

    def testSetTablePrefix(self):
        self.assertEqual(self.db.get_table_prefix(), 'exscriptd_')
        self.db.set_table_prefix('foo')
        self.assertEqual(self.db.get_table_prefix(), 'foo')
        self.db.install()
        self.db.uninstall()

    def testGetTablePrefix(self):
        self.testSetTablePrefix()

    def testAddOrder(self):
        self.testInstall()

        order1 = Order('fooservice')
        self.assertEqual(order1.get_created_by(), getuser())
        self.assertEqual(order1.get_description(), '')
        self.assertEqual(order1.get_progress(), .0)
        order1.created_by = 'this test'
        order1.set_description('my description')
        self.assertEqual(order1.get_created_by(), 'this test')
        self.assertEqual(order1.get_description(), 'my description')

        # Save the order.
        self.assertTrue(order1.get_id() is None)
        self.db.add_order(order1)
        order_id = order1.get_id()
        self.assertTrue(order_id is not None)

        def assert_progress(value):
            progress = self.db.get_order_progress_from_id(order_id)
            theorder = self.db.get_order(id = order_id)
            self.assertEqual(progress, value)
            self.assertEqual(theorder.get_progress(), value)

        # Check that the order is stored.
        order = self.db.get_order(id = order_id)
        self.assertEqual(order.get_id(), order_id)
        self.assertEqual(order.get_created_by(), 'this test')
        self.assertEqual(order.get_closed_timestamp(), None)
        self.assertEqual(order.get_description(), 'my description')
        assert_progress(.0)

        # Check that an order that has no tasks show progress 100% when
        # it is closed.
        order.close()
        self.db.save_order(order)
        assert_progress(1.0)

        # Add some sub-tasks.
        task1 = Task(order.id, 'my test task')
        self.db.save_task(task1)
        assert_progress(.0)

        task2 = Task(order.id, 'another test task')
        self.db.save_task(task2)
        assert_progress(.0)

        # Change the progress, re-check.
        task1.set_progress(.5)
        self.db.save_task(task1)
        assert_progress(.25)

        task2.set_progress(.5)
        self.db.save_task(task2)
        assert_progress(.5)

        task1.set_progress(1.0)
        self.db.save_task(task1)
        assert_progress(.75)

        task2.set_progress(1.0)
        self.db.save_task(task2)
        assert_progress(1.0)

    def testSaveOrder(self):
        self.testInstall()

        order1 = Order('fooservice')

        self.assertTrue(order1.get_id() is None)
        self.db.save_order(order1)

        # Check that the order is stored.
        order2 = self.db.get_order(id = order1.get_id())
        self.assertEqual(order1.get_id(), order2.get_id())

    def testGetOrderProgressFromId(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.save_order(order)
        id = order.get_id()
        self.assertEqual(self.db.get_order_progress_from_id(id), .0)

        order.close()
        self.db.save_order(order)
        self.assertEqual(self.db.get_order_progress_from_id(id), 1.0)

        task1 = Task(order.id, 'my test task')
        self.db.save_task(task1)
        self.assertEqual(self.db.get_order_progress_from_id(id), .0)

        task2 = Task(order.id, 'another test task')
        self.db.save_task(task2)
        self.assertEqual(self.db.get_order_progress_from_id(id), .0)

        task1.set_progress(.5)
        self.db.save_task(task1)
        self.assertEqual(self.db.get_order_progress_from_id(id), .25)
        task2.set_progress(.5)
        self.db.save_task(task2)
        self.assertEqual(self.db.get_order_progress_from_id(id), .5)
        task1.set_progress(1.0)
        self.db.save_task(task1)
        self.assertEqual(self.db.get_order_progress_from_id(id), .75)
        task2.set_progress(1.0)
        self.db.save_task(task2)
        self.assertEqual(self.db.get_order_progress_from_id(id), 1.0)

    def testGetOrder(self):
        self.testAddOrder()

    def testCountOrders(self):
        self.testInstall()
        self.assertEqual(self.db.count_orders(id = 1), 0)
        self.assertEqual(self.db.count_orders(), 0)
        self.testAddOrder()
        self.assertEqual(self.db.count_orders(), 1)
        self.testAddOrder()
        self.assertEqual(self.db.count_orders(), 2)
        self.assertEqual(self.db.count_orders(id = 1), 1)

    def testGetOrders(self):
        self.testAddOrder()
        self.testAddOrder()
        self.assertEqual(self.db.count_orders(), 2)
        orders = self.db.get_orders()
        self.assertEqual(len(orders), 2)

    def testCloseOpenOrders(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.add_order(order)
        order = self.db.get_orders()[0]
        self.assertEqual(order.closed, None)

        self.db.close_open_orders()
        order = self.db.get_orders()[0]
        self.assertNotEqual(order.get_closed_timestamp(), None)

    def testSaveTask(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.save_order(order)

        task = Task(order.id, 'my test task')
        self.assertTrue(task.id is None)
        self.db.save_task(task)
        self.assertTrue(task.id is not None)

    def testGetTask(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.save_order(order)

        task1 = Task(order.id, 'my test task')
        self.db.save_task(task1)
        loaded_task = self.db.get_task()
        self.assertEqual(task1.id, loaded_task.id)

        task2 = Task(order.id, 'another test task')
        self.db.save_task(task2)
        self.assertRaises(IndexError, self.db.get_task)

    def testGetTasks(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.save_order(order)

        task1 = Task(order.id, 'my test task')
        task2 = Task(order.id, 'another test task')
        self.db.save_task(task1)
        self.db.save_task(task2)

        id_list1 = sorted([task1.id, task2.id])
        id_list2 = sorted([task.id for task in self.db.get_tasks()])
        self.assertEqual(id_list1, id_list2)

        tasks    = self.db.get_tasks(order_id = order.id)
        id_list2 = sorted([task.id for task in tasks])
        self.assertEqual(id_list1, id_list2)

        id_list2 = [task.id for task in self.db.get_tasks(order_id = 2)]
        self.assertEqual([], id_list2)

    def testCountTasks(self):
        self.testInstall()
        self.assertEqual(self.db.count_tasks(), 0)
        self.testSaveTask()
        self.assertEqual(self.db.count_tasks(), 1)
        self.testSaveTask()
        self.assertEqual(self.db.count_tasks(), 2)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OrderDBTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
