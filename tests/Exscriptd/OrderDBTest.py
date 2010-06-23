import sys, unittest, re, os.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

def suite():
    tests = ['testOrderDB']
    return unittest.TestSuite(map(OrderDBTest, tests))

import MySQLdb
from sqlalchemy        import create_engine
from sqlalchemy.orm    import clear_mappers
from ConfigParser      import RawConfigParser
from Exscript          import Host
from Exscriptd.Order   import Order
from Exscriptd.OrderDB import OrderDB

class OrderDBTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        clear_mappers()

    def testOrderDB(self):
        order1 = Order('fooservice')
        host1  = Host('foohost1')
        host2  = Host('foohost2')
        host1.set('foovar1', 'value1')
        host1.set('foovar2', 'value2')
        host2.set('foovar1', 'value1')
        host2.set('foovar2', 'value3')
        order1.add_host(host1)
        order1.add_host(host2)

        self.assert_(order1.get_id())
        db = OrderDB(self.engine)
        db.install()
        db.add_order(order1)

        # Check that the order is stored.
        order2 = db.get_order(id = order1.get_id())
        self.assert_(order1.get_id() == order2.get_id())

        # Check that the hosts of the order are stored.
        hosts1 = [h.get_address() for h in order1.get_hosts()]
        hosts2 = [h.get_address() for h in order2.get_hosts()]
        self.assertEqual(hosts1, hosts2)

        # Check that the variables of the hosts are stored.
        hosts2 = order2.get_hosts()
        self.assertEqual(host1.get_all(), hosts2[0].get_all())
        self.assertEqual(host2.get_all(), hosts2[1].get_all())

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity = 2).run(suite())
