# Copyright (C) 2007 Samuel Abels, http://debain.org
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
import getpass

def get_login():
    """
    Returns a tuple containing the username and the password.
    May throw an exception if EOF is given by the user.
    """
    # Read username and password.
    try:
        env_user = getpass.getuser()
        user     = raw_input('Please enter your user name [%s]: ' % env_user)
        if user == '':
            user = env_user
    except:
        user = raw_input('Please enter your user name: ' % user)
    password = getpass.getpass('Please enter your password: ')
    return (user, password)
