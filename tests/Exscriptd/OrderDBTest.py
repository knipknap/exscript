import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from sqlalchemy        import create_engine
from Exscriptd.Order   import Order
from Exscriptd.Task    import Task
from Exscriptd.OrderDB import OrderDB

class OrderDBTest(unittest.TestCase):
    CORRELATE = OrderDB

    def setUp(self):
        self.engine = create_engine('sqlite://')
        self.db     = OrderDB(self.engine)

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
        self.assert_(len(orders) == 0)

    def testDebug(self):
        self.assert_(not self.engine.echo)
        self.db.debug()
        self.assert_(self.engine.echo)
        self.db.debug(False)
        self.assert_(not self.engine.echo)

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
        self.assertEqual(order1.get_created_by(), os.environ.get('USER'))
        self.assertEqual(order1.get_description(), '')
        order1.created_by = 'this test'
        order1.set_description('my description')
        self.assertEqual(order1.get_created_by(), 'this test')
        self.assertEqual(order1.get_description(), 'my description')

        self.assert_(order1.get_id() is None)
        self.db.add_order(order1)

        # Check that the order is stored.
        order2 = self.db.get_order(id = order1.get_id())
        self.assertEqual(order1.get_id(), order2.get_id())
        self.assertEqual(order2.get_created_by(), 'this test')
        self.assertEqual(order2.get_description(), 'my description')

    def testSaveOrder(self):
        self.testInstall()

        order1 = Order('fooservice')

        self.assert_(order1.get_id() is None)
        self.db.save_order(order1)

        # Check that the order is stored.
        order2 = self.db.get_order(id = order1.get_id())
        self.assertEqual(order1.get_id(), order2.get_id())

    def testGetOrder(self):
        self.testAddOrder()

    def testCountOrders(self):
        self.testInstall()
        self.assertEqual(self.db.count_orders(), 0)
        self.testAddOrder()
        self.assertEqual(self.db.count_orders(), 1)
        self.testAddOrder()
        self.assertEqual(self.db.count_orders(), 2)

    def testGetOrders(self):
        self.testAddOrder()
        self.testAddOrder()
        self.assertEqual(self.db.count_orders(), 2)
        orders = self.db.get_orders()
        self.assertEqual(len(orders), 2)

    def testCloseOpenOrders(self):
        self.testAddOrder()
        self.assertEqual(self.db.count_orders(), 1)

        order = self.db.get_orders()[0]
        self.assertEqual(order.closed, None)

        self.db.close_open_orders()
        order = self.db.get_orders()[0]
        self.failIfEqual(order.get_closed_timestamp(), None)

    def testSaveTask(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.save_order(order)

        task = Task('my test task')
        self.assert_(task.id is None)
        self.db.save_task(order, task)
        self.assert_(task.id is not None)

    def testGetTask(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.save_order(order)

        task1 = Task('my test task')
        self.db.save_task(order, task1)
        self.assertEqual(task1.id, self.db.get_task().id)

        task2 = Task('another test task')
        self.db.save_task(order, task2)
        self.assertRaises(IndexError, self.db.get_task)

    def testGetTasks(self):
        self.testInstall()

        order = Order('fooservice')
        self.db.save_order(order)

        task1 = Task('my test task')
        task2 = Task('another test task')
        self.db.save_task(order, task1)
        self.db.save_task(order, task2)

        id_list1 = sorted([task1.id, task2.id])
        id_list2 = sorted([task.id for task in self.db.get_tasks()])
        self.assertEqual(id_list1, id_list2)

        tasks    = self.db.get_tasks(order_id = order.id)
        id_list2 = sorted([task.id for task in tasks])
        self.assertEqual(id_list1, id_list2)

        id_list2 = [task.id for task in self.db.get_tasks(order_id = 2)]
        self.assertEqual([], id_list2)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OrderDBTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
