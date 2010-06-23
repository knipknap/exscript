from Order              import Order
from Exscript           import Host
from Exscript.util.cast import to_list
import sqlalchemy                 as sa
import sqlalchemy.databases.mysql as mysql

class OrderDB(object):
    """
    The main interface for accessing the database.
    """

    def __init__(self, engine):
        """
        Instantiates a new OrderDB.
        
        @type  db: object
        @param db: An sqlalchemy database connection.
        @rtype:  DB
        @return: The new instance.
        """
        self.engine        = engine
        self.metadata      = sa.MetaData(self.engine)
        self._table_prefix = 'ips_'
        self._table_map    = {}
        self.__update_table_names()

    def __add_table(self, table):
        """
        Adds a new table to the internal table list.
        
        @type  table: Table
        @param table: An sqlalchemy table.
        """
        pfx = self._table_prefix
        self._table_map[table.name[len(pfx):]] = table

    def __update_table_names(self):
        """
        Adds all tables to the internal table list.
        """
        pfx = self._table_prefix
        self.__add_table(sa.Table(pfx + 'order', self.metadata,
            sa.Column('id',      sa.String(50), primary_key = True),
            sa.Column('service', sa.String(50), index = True),
            sa.Column('status',  sa.String(20), index = True),
            mysql_engine = 'INNODB'
        ))

        self.__add_table(sa.Table(pfx + 'host', self.metadata,
            sa.Column('id',       sa.Integer,     primary_key = True),
            sa.Column('order_id', sa.String(50),  index = True),
            sa.Column('address',  sa.String(150), index = True),
            sa.Column('name',     sa.String(150), index = True),
            sa.ForeignKeyConstraint(['order_id'], [pfx + 'order.id'], ondelete = 'CASCADE'),
            mysql_engine = 'INNODB'
        ))

        self.__add_table(sa.Table(pfx + 'variable', self.metadata,
            sa.Column('id',      sa.Integer,     primary_key = True),
            sa.Column('host_id', sa.Integer,     index = True),
            sa.Column('name',    sa.String(150), index = True),
            sa.Column('value',   sa.String(150), index = True),
            sa.ForeignKeyConstraint(['host_id'], [pfx + 'host.id'], ondelete = 'CASCADE'),
            mysql_engine = 'INNODB'
        ))

    def install(self):
        """
        Installs (or upgrades) database tables.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        self.metadata.create_all()
        return True


    def uninstall(self):
        """
        Drops all tables from the database. Use with care.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        self.metadata.drop_all()
        return True


    def clear_database(self):
        """
        Drops the content of any database table used by this library.
        Use with care.

        Wipes out everything, including types, actions, resources and acls.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        delete = self._table_map['order'].delete()
        delete.execute()
        return True

    def debug(self, debug = True):
        """
        Enable/disable debugging.

        @type  debug: Boolean
        @param debug: True to enable debugging.
        """
        if debug:
            self.engine.echo = 1
        else:
            self.engine.echo = 0

    def set_table_prefix(self, prefix):
        """
        Define a string that is prefixed to all table names in the database.
        Default is 'guard_'.

        @type  prefix: string
        @param prefix: The new prefix.
        """
        self._table_prefix = prefix
        self.__update_table_names()

    def get_table_prefix(self):
        """
        Returns the current database table prefix.
        
        @rtype:  string
        @return: The current prefix.
        """
        return self._table_prefix

    def __add_variable(self, host_id, key, value):
        """
        Inserts the given variable into the database.
        """
        if host_id is None:
            raise AttributeError('host_id argument must not be None')
        if key is None:
            raise AttributeError('key argument must not be None')

        insert = self._table_map['variable'].insert()
        result = insert.execute(host_id = host_id,
                                name    = key,
                                value   = value)
        return result.last_inserted_ids()[0]

    def __get_variable_from_row(self, row):
        assert row is not None
        tbl_v = self._table_map['variable']
        return row[tbl_v.c.name], row[tbl_v.c.value]

    def __add_host(self, order_id, host):
        """
        Inserts the given host into the database.
        """
        if order_id is None:
            raise AttributeError('order_id argument must not be None')
        if host is None:
            raise AttributeError('host argument must not be None')

        # Insert the host.
        insert = self._table_map['host'].insert()
        result = insert.execute(order_id = order_id,
                                name     = host.get_name(),
                                address  = host.get_address())
        host_id = result.last_inserted_ids()[0]

        # Insert the host's variables.
        for key, value in host.get_all().iteritems():
            self.__add_variable(host_id, key, value)
        return host_id

    def __get_host_from_row(self, row):
        assert row is not None
        tbl_h = self._table_map['host']
        host  = Host(row[tbl_h.c.name])
        host.set_address(row[tbl_h.c.address])
        return host

    def __add_order(self, order):
        """
        Inserts the given order into the database.
        """
        if order is None:
            raise AttributeError('order argument must not be None')

        # Insert the order
        insert = self._table_map['order'].insert()
        result = insert.execute(id      = order.get_id(),
                                service = order.get_service_name(),
                                status  = order.get_status())

        # Insert the hosts of the order.
        for host in order.get_hosts():
            self.__add_host(order.get_id(), host)
        return result.last_inserted_ids()[0]

    def __get_order_from_row(self, row):
        assert row is not None
        tbl_a        = self._table_map['order']
        order        = Order(row[tbl_a.c.service])
        order.id     = row[tbl_a.c.id]
        order.status = row[tbl_a.c.status]
        return order

    def __get_orders_from_query(self, query):
        """
        Returns a list of orders, including their hosts and variables.
        """
        assert query is not None
        result = query.execute()

        row = result.fetchone()
        if not row:
            return []

        tbl_o         = self._table_map['order']
        tbl_h         = self._table_map['host']
        tbl_v         = self._table_map['variable']
        last_order_id = row[tbl_o.c.id]
        order_list    = []
        while row is not None:
            last_order_id = row[tbl_o.c.id]
            if not last_order_id:
                break

            order = self.__get_order_from_row(row)
            order_list.append(order)

            if not row[tbl_h.c.id]:
                row = result.fetchone()
                continue

            # Append all hosts.
            while row and row[tbl_h.c.id]:
                if last_order_id != row[tbl_o.c.id]:
                    break

                last_host_id = row[tbl_h.c.id]
                host         = self.__get_host_from_row(row)
                order.add_host(host)

                if not row[tbl_v.c.host_id]:
                    row = result.fetchone()
                    continue

                # Append the host's variables.
                while row and row[tbl_v.c.host_id]:
                    key, value = self.__get_variable_from_row(row)
                    host.set(key, value)

                    row = result.fetchone()
                    if not row or last_host_id != row[tbl_h.c.id]:
                        break

            if not row or last_order_id != row[tbl_o.c.id]:
                break

        return order_list


    def get_order(self, **kwargs):
        """
        Like get_orders(), but
          - Returns None, if no match was found.
          - Returns the order, if exactly one match was found.
          - Raises an error if more than one match was found.

        @type  kwargs: dict
        @param kwargs: For a list of allowed keys see get_orders().
        @rtype:  Order
        @return: The order or None.
        """
        result = self.get_orders(0, 2, **kwargs)
        if len(result) == 0:
            return None
        elif len(result) > 1:
            raise Exception('Too many results')
        return result[0]


    def get_orders(self, offset = 0, limit = 0, **kwargs):
        """
        Returns all orders that match the given criteria.
        
        @type  offset: int
        @param offset: The offset of the first item to be returned.
        @type  limit: int
        @param limit: The maximum number of items that is returned.
        @type  kwargs: dict
        @param kwargs: The following keys may be used:
                         - id - the id of the order (str)
                         - service - the service name (str)
                         - status - the status (str)
                       All values may also be lists (logical OR).
        @rtype:  list[Order]
        @return: The list of orders.
        """
        tbl_o = self._table_map['order']
        tbl_h = self._table_map['host']
        tbl_v = self._table_map['variable']
        table = tbl_o.outerjoin(tbl_h, tbl_o.c.id == tbl_h.c.order_id)
        table = table.outerjoin(tbl_v, tbl_h.c.id == tbl_v.c.host_id)
        where = None

        # Search conditions.
        for field in ('id', 'service', 'status'):
            if kwargs.has_key(field):
                cond = None
                for value in to_list(kwargs.get(field)):
                    cond = sa.or_(cond, tbl_o.c[field] == value)
                where = sa.and_(where, cond)

        # Select the orders (subselect).
        order_select = sa.select([tbl_o.c.id.label('order_id')],
                                 where,
                                 offset     = offset).alias('orders')

        # Select all hosts from the order.
        select = table.select(tbl_o.c.id == order_select.c.order_id,
                              use_labels = True)

        return self.__get_orders_from_query(select)


##################################################
# FIXME: everything below is not yet ported
#
    def add_order(self, orders):
        """
        Inserts the given order into the database.

        @type  orders: Order|list[Order]
        @param orders: The orders to be added.
        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        if orders is None:
            raise AttributeError('order argument must not be None')
        for order in to_list(orders):
            self.__add_order(order)
        return True


    def __save_order1(self, order):
        """
        Updates the given order in the database. Does nothing if the
        order is not yet in the database.

        @type  order: Order
        @param order: The order to be saved.
        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        if order is None:
            raise AttributeError('order argument must not be None')
        if order.__class__.__name__ not in self._types:
            raise AttributeError('order type is not yet registered')

        table  = self._table_map['order']
        update = table.update(table.c.id == order.get_id())
        update.execute(order_type = order.__class__.__name__,
                       handle      = order.get_handle(),
                       name        = order.get_name())
        self._order_cache_flush()
        self._order_cache_add(order)
        return True


    def save_order(self, orders):
        """
        Updates the given orders in the database. Does nothing if
        the order doesn't exist.

        @type  orders: Order|list[Order]
        @param orders: The order to be saved.
        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        if orders is None:
            raise AttributeError('order argument must not be None')
        if type(orders) != type([]):
            orders = [orders]
        for order in orders:
            self.__save_order1(order)
        return True


    def delete_order(self, orders):
        """
        Convenience wrapper around delete_order_from_match().

        @type  orders: Order|list[Order]
        @param orders: The orders to be removed.
        @rtype:  int
        @return: The number of deleted orders.
        """
        if orders is None:
            raise AttributeError('order argument must not be None')
        if type(orders) != type([]):
            orders = [orders]
        ids = [order.get_id() for order in orders]
        res = self.delete_order_from_match(id = ids)
        for order in orders:
            order.set_id(None)
        return res


    def delete_order_from_match(self, **kwargs):
        """
        Deletes all orders that match the given criteria from the
        database.
        All ACLs associated with the order are removed.

        @type  kwargs: dict
        @param kwargs: The following keys may be used:
                         - id - the id of the resource
                         - handle - the handle of the resource
                         - type - the class type of the resource
                       All values may also be lists (logical OR).
        @rtype:  int
        @return: The number of deleted orders.
        """
        tbl_a = self._table_map['order']
        table = tbl_a
        where = None

        # ID.
        if kwargs.has_key('id'):
            ids = kwargs.get('id')
            if type(ids) == type(0):
                ids = [ids]
            id_where = None
            for current_id in ids:
                id_where = sa.or_(id_where, table.c.id == current_id)
            where = sa.and_(where, id_where)

        # Handle.
        if kwargs.has_key('handle'):
            handles = kwargs.get('handle')
            if type(handles) != type([]):
                handles = [handles]
            handle_where = None
            for handle in handles:
                handle_where = sa.or_(handle_where, table.c.handle == handle)
            where = sa.and_(where, handle_where)

        # Object type.
        if kwargs.has_key('type'):
            types = kwargs.get('type')
            cond  = self._get_subtype_sql(tbl_a.c.order_type, types)
            where = sa.and_(where, cond)

        delete = table.delete(where)
        result = delete.execute()

        if result.rowcount > 0:
            self._order_cache_flush()
        return result.rowcount
