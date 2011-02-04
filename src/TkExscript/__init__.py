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
"""
Contains graphical user interfaces using Python's tkinter.
"""
from TkExscript.LoginWidget import LoginWidget
from TkExscript.LoginWindow import LoginWindow
from TkExscript.MailWidget  import MailWidget
from TkExscript.MailWindow  import MailWindow
from TkExscript.Notebook    import Notebook
from TkExscript.ProgressBar import ProgressBar
from TkExscript.QueueWidget import QueueWidget
from TkExscript.QueueWindow import QueueWindow

import inspect
__all__ = [name for name, obj in locals().items()
           if not (name.startswith('_') or inspect.ismodule(obj))]
