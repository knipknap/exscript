# Copyright (C) 2007-2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from datetime import datetime
import sqlalchemy as sa
from Exscript.util.cast import to_list
from Exscript.util.impl import synchronized
from Exscriptd.Order import Order
from Exscriptd.Task import Task

# Note: The synchronized decorator is used because
# sqlite does not support concurrent writes, so we need to
# do this to have graceful locking (rather than sqlite's
# hard locking).

class OrderDB(object):
    """
    The main interface for accessing the database.
    """

    def __init__(self, engine):
        """
        Instantiates a new OrderDB.
        
        @type  engine: object
        @param engine: An sqlalchemy database engine.
        @rtype:  OrderDB
        @return: The new instance.
        """
        self.engine        = engine
        self.metadata      = sa.MetaData(self.engine)
        self._table_prefix = 'exscriptd_'
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
            sa.Column('id',          sa.Integer,    primary_key = True),
            sa.Column('service',     sa.String(50), index = True),
            sa.Column('status',      sa.String(20), index = True),
            sa.Column('description', sa.String(150)),
            sa.Column('created',     sa.DateTime,   default = datetime.utcnow),
            sa.Column('closed',      sa.DateTime),
            sa.Column('created_by',  sa.String(50)),
            mysql_engine = 'INNODB'
        ))

        self.__add_table(sa.Table(pfx + 'task', self.metadata,
            sa.Column('id',        sa.Integer,     primary_key = True),
            sa.Column('order_id',  sa.Integer,     index = True),
            sa.Column('job_id',    sa.String(33),  index = True),
            sa.Column('name',      sa.String(150), index = True),
            sa.Column('status',    sa.String(150), index = True),
            sa.Column('progress',  sa.Float,       default = 0.0),
            sa.Column('started',   sa.DateTime,    default = datetime.utcnow),
            sa.Column('closed',    sa.DateTime,    index = True),
            sa.Column('logfile',   sa.String(250)),
            sa.Column('tracefile', sa.String(250)),
            sa.Column('vars',      sa.PickleType()),
            sa.ForeignKeyConstraint(['order_id'], [pfx + 'order.id'], ondelete = 'CASCADE'),
            mysql_engine = 'INNODB'
        ))


    @synchronized
    def install(self):
        """
        Installs (or upgrades) database tables.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        self.metadata.create_all()
        return True

    @synchronized
    def uninstall(self):
        """
        Drops all tables from the database. Use with care.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        """
        self.metadata.drop_all()
        return True

    @synchronized
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
        self.engine.echo = debug

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

    @synchronized
    def __add_task(self, task):
        """
        Inserts the given task into the database.
        """
        if task is None:
            raise AttributeError('task argument must not be None')
        if task.order_id is None:
            raise AttributeError('order_id must not be None')

        if not task.is_dirty():
            return

        # Insert the task
        insert  = self._table_map['task'].insert()
        result  = insert.execute(**task.todict())
        task_id = result.last_inserted_ids()[0]

        task.untouch()
        return task_id

    @synchronized
    def __save_task(self, task):
        """
        Inserts or updates the given task into the database.
        """
        if task is None:
            raise AttributeError('task argument must not be None')
        if task.order_id is None:
            raise AttributeError('order_id must not be None')

        if not task.is_dirty():
            return

        # Insert or update the task.
        tbl_t  = self._table_map['task']
        fields = task.todict()
        if task.id is None:
            query   = tbl_t.insert()
            result  = query.execute(**fields)
            task.id = result.last_inserted_ids()[0]
        else:
            query   = tbl_t.update(tbl_t.c.id == task.id)
            result  = query.execute(**fields)

        task.untouch()
        return task.id

    def __get_task_from_row(self, row):
        assert row is not None
        tbl_t          = self._table_map['task']
        task           = Task(row[tbl_t.c.order_id], row[tbl_t.c.name])
        task.id        = row[tbl_t.c.id]
        task.job_id    = row[tbl_t.c.job_id]
        task.status    = row[tbl_t.c.status]
        task.progress  = row[tbl_t.c.progress]
        task.started   = row[tbl_t.c.started]
        task.closed    = row[tbl_t.c.closed]
        task.logfile   = row[tbl_t.c.logfile]
        task.tracefile = row[tbl_t.c.tracefile]
        task.vars      = row[tbl_t.c.vars]
        task.untouch()
        return task

    def __get_tasks_from_query(self, query):
        """
        Returns a list of tasks.
        """
        assert query is not None
        result = query.execute()
        return [self.__get_task_from_row(row) for row in result]

    def __get_tasks_cond(self, **kwargs):
        tbl_t = self._table_map['task']

        # Search conditions.
        where = None
        for field in ('id',
                      'order_id',
                      'job_id',
                      'name',
                      'status',
                      'opened',
                      'closed'):
            if field in kwargs:
                cond = None
                for value in to_list(kwargs.get(field)):
                    cond = sa.or_(cond, tbl_t.c[field] == value)
                where = sa.and_(where, cond)

        return where

    def __get_tasks_query(self, fields, offset, limit, **kwargs):
        tbl_t = self._table_map['task']
        where = self.__get_tasks_cond(**kwargs)
        return sa.select(fields,
                         where,
                         from_obj = [tbl_t],
                         order_by = [sa.desc(tbl_t.c.id)],
                         offset   = offset,
                         limit    = limit)

    def __get_orders_cond(self, **kwargs):
        tbl_o = self._table_map['order']

        # Search conditions.
        where = None
        for field in ('id', 'service', 'description', 'status', 'created_by'):
            values = kwargs.get(field)
            if values is not None:
                cond = None
                for value in to_list(values):
                    cond = sa.or_(cond, tbl_o.c[field].like(value))
                where = sa.and_(where, cond)

        return where

    def __get_orders_query(self, offset = 0, limit = None, **kwargs):
        tbl_o  = self._table_map['order']
        tbl_t  = self._table_map['task']
        where  = self.__get_orders_cond(**kwargs)
        fields = list(tbl_o.c)
        table  = tbl_o.outerjoin(tbl_t, tbl_t.c.order_id == tbl_o.c.id)
        fields.append(sa.func.avg(tbl_t.c.progress).label('avg_progress'))
        return sa.select(fields,
                         where,
                         from_obj   = [table],
                         group_by   = [tbl_o.c.id],
                         order_by   = [sa.desc(tbl_o.c.id)],
                         offset     = offset,
                         limit      = limit)

    @synchronized
    def __add_order(self, order):
        """
        Inserts the given order into the database.
        """
        if order is None:
            raise AttributeError('order argument must not be None')

        # Insert the order
        insert   = self._table_map['order'].insert()
        fields   = dict(k for k in order.todict().iteritems()
                        if k[0] not in ('id', 'created', 'progress'))
        result   = insert.execute(**fields)
        order.id = result.last_inserted_ids()[0]
        return order.id

    @synchronized
    def __save_order(self, order):
        """
        Updates the given order in the database. Does nothing if the
        order is not yet in the database.

        @type  order: Order
        @param order: The order to be saved.
        """
        if order is None:
            raise AttributeError('order argument must not be None')

        # Check if the order already exists.
        if order.id:
            theorder = self.get_order(id = order.get_id())
        else:
            theorder = None

        # Insert or update it.
        if not theorder:
            return self.add_order(order)
        table  = self._table_map['order']
        fields = dict(k for k in order.todict().iteritems()
                      if k[0] not in ('id', 'created', 'progress'))
        query  = table.update(table.c.id == order.get_id())
        query.execute(**fields)

    def __get_order_from_row(self, row):
        assert row is not None
        tbl_a            = self._table_map['order']
        order            = Order(row[tbl_a.c.service])
        order.id         = row[tbl_a.c.id]
        order.status     = row[tbl_a.c.status]
        order.created    = row[tbl_a.c.created]
        order.closed     = row[tbl_a.c.closed]
        order.created_by = row[tbl_a.c.created_by]
        order.set_description(row[tbl_a.c.description])
        try:
            order.progress = float(row.avg_progress)
        except TypeError: # Order has no tasks
            if order.closed:
                order.progress = 1.0
            else:
                order.progress = .0
        return order

    def __get_orders_from_query(self, query):
        """
        Returns a list of orders.
        """
        assert query is not None
        result = query.execute()
        return [self.__get_order_from_row(row) for row in result]

    def count_orders(self, **kwargs):
        """
        Returns the total number of orders matching the given criteria.

        @rtype:  int
        @return: The number of orders.
        @type  kwargs: dict
        @param kwargs: For a list of allowed keys see get_orders().
        """
        tbl_o = self._table_map['order']
        where = self.__get_orders_cond(**kwargs)
        return tbl_o.count(where).execute().fetchone()[0]

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
            raise IndexError('Too many results')
        return result[0]

    def get_orders(self, offset = 0, limit = None, **kwargs):
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
                         - description - the order description (str)
                         - status - the status (str)
                       All values may also be lists (logical OR).
        @rtype:  list[Order]
        @return: The list of orders.
        """
        select = self.__get_orders_query(avg    = True,
                                         offset = offset,
                                         limit  = limit,
                                         **kwargs)
        return self.__get_orders_from_query(select)

    def add_order(self, orders):
        """
        Inserts the given order into the database.

        @type  orders: Order|list[Order]
        @param orders: The orders to be added.
        """
        if orders is None:
            raise AttributeError('order argument must not be None')
        with self.engine.contextual_connect(close_with_result = True).begin():
            for order in to_list(orders):
                self.__add_order(order)

    def close_open_orders(self):
        """
        Sets the 'closed' timestamp of all orders that have none, without
        changing the status field.
        """
        closed = datetime.utcnow()
        tbl_o  = self._table_map['order']
        tbl_t  = self._table_map['task']
        query1 = tbl_t.update(tbl_t.c.closed == None)
        query2 = tbl_o.update(tbl_o.c.closed == None)
        query1.execute(closed = closed)
        query2.execute(closed = closed)

    def save_order(self, orders):
        """
        Updates the given orders in the database. Does nothing if
        the order doesn't exist.

        @type  orders: Order|list[Order]
        @param orders: The order to be saved.
        """
        if orders is None:
            raise AttributeError('order argument must not be None')

        with self.engine.contextual_connect(close_with_result = True).begin():
            for order in to_list(orders):
                self.__save_order(order)

    def get_order_progress_from_id(self, id):
        """
        Returns the progress of the order in percent.

        @type  id: int
        @param id: The id of the order.
        @rtype:  float
        @return: A float between 0.0 and 1.0
        """
        order = self.get_order(id = id)
        return order.get_progress()

    def count_tasks(self, **kwargs):
        """
        Returns the number of matching tasks in the DB.

        @type  kwargs: dict
        @param kwargs: See L{get_tasks()}.
        @rtype:  int
        @return: The number of tasks.
        """
        tbl_t = self._table_map['task']
        where = self.__get_tasks_cond(**kwargs)
        query = tbl_t.count(where)
        return query.execute().fetchone()[0]

    def get_task(self, **kwargs):
        """
        Like get_tasks(), but
          - Returns None, if no match was found.
          - Returns the task, if exactly one match was found.
          - Raises an error if more than one match was found.

        @type  kwargs: dict
        @param kwargs: For a list of allowed keys see get_tasks().
        @rtype:  Task
        @return: The task or None.
        """
        result = self.get_tasks(0, 2, **kwargs)
        if len(result) == 0:
            return None
        elif len(result) > 1:
            raise IndexError('Too many results')
        return result[0]

    def get_tasks(self, offset = 0, limit = None, **kwargs):
        """
        Returns all tasks that match the given criteria.

        @type  offset: int
        @param offset: The offset of the first item to be returned.
        @type  limit: int
        @param limit: The maximum number of items that is returned.
        @type  kwargs: dict
        @param kwargs: The following keys may be used:
                         - id - the id of the task (int)
                         - order_id - the order id of the task (int)
                         - job_id - the job id of the task (str)
                         - name - the name (str)
                         - status - the status (str)
                       All values may also be lists (logical OR).
        @rtype:  list[Task]
        @return: The list of tasks.
        """
        tbl_t  = self._table_map['task']
        fields = list(tbl_t.c)
        query  = self.__get_tasks_query(fields, offset, limit, **kwargs)
        return self.__get_tasks_from_query(query)

    def save_task(self, task):
        """
        Inserts or updates the given task in the database.

        @type  order: Order
        @param order: The order for which a task is added.
        @type  task: Task
        @param task: The task to be saved.
        """
        if task is None:
            raise AttributeError('task argument must not be None')
        if task.order_id is None:
            raise AttributeError('order id must not be None')

        if not task.is_dirty():
            return

        return self.__save_task(task)

    @synchronized
    def mark_tasks(self, new_status, offset = 0, limit = None, **kwargs):
        """
        Returns all tasks that match the given criteria and changes
        their status to the given value.

        @type  new_status: str
        @param new_status: The new status.
        @type  offset: int
        @param offset: The offset of the first item to be returned.
        @type  limit: int
        @param limit: The maximum number of items that is returned.
        @type  kwargs: dict
        @param kwargs: See L{get_tasks()}.
        @rtype:  list[Task]
        @return: The list of tasks.
        """
        tbl_t = self._table_map['task']

        # Find the ids of the matching tasks.
        where     = self.__get_tasks_cond(**kwargs)
        id_select = sa.select([tbl_t.c.id],
                              where,
                              from_obj = [tbl_t],
                              order_by = [tbl_t.c.id],
                              offset   = offset,
                              limit    = limit)
        id_list = [row.id for row in id_select.execute()]

        # Update the status of those tasks.
        query  = tbl_t.update(tbl_t.c.id.in_(id_list))
        result = query.execute(status = new_status)

        # Now create a Task object for each of those tasks.
        all_select = tbl_t.select(tbl_t.c.id.in_(id_list),
                                  order_by = [tbl_t.c.id])
        return self.__get_tasks_from_query(all_select)
