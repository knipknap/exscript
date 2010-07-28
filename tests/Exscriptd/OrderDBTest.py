import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from sqlalchemy        import create_engine
from Exscript          import Host
from Exscriptd.Order   import Order
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
        host1  = Host('foohost1')
        host2  = Host('foohost2')
        host1.set('foovar1', 'value1')
        host1.set('foovar2', 'value2')
        host2.set('foovar1', 'value1')
        host2.set('foovar2', 'value3')
        order1.add_host(host1)
        order1.add_host(host2)

        self.assert_(order1.get_id() is None)
        self.db.add_order(order1)

        # Check that the order is stored.
        order2 = self.db.get_order(id = order1.get_id())
        self.assert_(order1.get_id() == order2.get_id())

        # Check that the hosts of the order are stored.
        hosts1 = [h.get_address() for h in order1.get_hosts()]
        hosts2 = [h.get_address() for h in order2.get_hosts()]
        self.assertEqual(hosts1, hosts2)

        # Check that the variables of the hosts are stored.
        hosts2 = order2.get_hosts()
        self.assertEqual(host1.get_all(), hosts2[0].get_all())
        self.assertEqual(host2.get_all(), hosts2[1].get_all())

    def testSaveOrder(self):
        self.testInstall()

        order1 = Order('fooservice')
        host1  = Host('foohost1')
        host2  = Host('foohost2')
        host1.set('foovar1', 'value1')
        host1.set('foovar2', 'value2')
        host2.set('foovar1', 'value1')
        host2.set('foovar2', 'value3')
        order1.add_host(host1)
        order1.add_host(host2)

        self.assert_(order1.get_id() is None)
        self.db.save_order(order1)

        # Check that the order is stored.
        order2 = self.db.get_order(id = order1.get_id())
        self.assert_(order1.get_id() == order2.get_id())

        # Check that the hosts of the order are stored.
        hosts1 = [h.get_address() for h in order1.get_hosts()]
        hosts2 = [h.get_address() for h in order2.get_hosts()]
        self.assertEqual(hosts1, hosts2)

        # Check that the variables of the hosts are stored.
        hosts2 = order2.get_hosts()
        self.assertEqual(host1.get_all(), hosts2[0].get_all())
        self.assertEqual(host2.get_all(), hosts2[1].get_all())

    def testGetOrder(self):
        self.testAddOrder()

    def testGetOrders(self):
        pass #FIXME

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(OrderDBTest)
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
