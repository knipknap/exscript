import sys
import unittest
import re
import os.path
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from getpass import getuser
import Exscript.util.mail
from Exscript.util.mail import Mail

vars = dict(testvar1='blah', testvar2='foo', testvar3='bar')
template = '''
To: user, user2@localhost
Cc: user3
Bcc: user4
Subject: Blah blah {testvar1}

Test body: {testvar2}
{testvar3}
'''.strip()

smtp = '''
From: test
To: user,
 user2@localhost
Cc: user3
Bcc: user4
Subject: Blah blah {testvar1}

Test body: {testvar2}
{testvar3}
'''.strip().replace('\n', '\r\n')


class MailTest(unittest.TestCase):
    CORRELATE = Mail

    def setUp(self):
        self.mail = Mail(sender='test')

    def testConstructor(self):
        mail = Mail()
        self.failIfEqual(mail.get_sender(), None)
        self.failIfEqual(mail.get_sender(), '')
        user = getuser()
        self.assert_(mail.get_sender().startswith(user + '@'))

    def testSetFromTemplateString(self):
        self.mail.set_from_template_string(template)
        tmpl = self.mail.get_smtp_mail().strip()
        self.assertEqual(tmpl, smtp)
        head = self.mail.get_smtp_header().strip()
        self.assert_(tmpl.startswith(head))

    def testSetSender(self):
        self.assertEqual(self.mail.get_sender(), 'test')
        self.mail.set_sender('test2')
        self.assertEqual(self.mail.get_sender(), 'test2')

    def testGetSender(self):
        pass  # see testSetSender()

    def checkSetAddr(self, set_method, get_method):
        set_method('test')
        self.assertEqual(get_method(), ['test'])

        set_method(['test1', 'test2'])
        self.assertEqual(get_method(), ['test1', 'test2'])

        set_method('test1, test2')
        self.assertEqual(get_method(), ['test1', 'test2'])

    def checkAddAddr(self, add_method, get_method):
        add_method(['test1', 'test2'])
        self.assertEqual(get_method(), ['test1', 'test2'])

        add_method('test3, test4')
        self.assertEqual(get_method(), ['test1', 'test2', 'test3', 'test4'])

    def testSetTo(self):
        self.checkSetAddr(self.mail.set_to, self.mail.get_to)

    def testAddTo(self):
        self.checkAddAddr(self.mail.add_to, self.mail.get_to)

    def testGetTo(self):
        pass  # see testSetTo()

    def testSetCc(self):
        self.checkSetAddr(self.mail.set_cc, self.mail.get_cc)

    def testAddCc(self):
        self.checkAddAddr(self.mail.add_cc, self.mail.get_cc)

    def testGetCc(self):
        pass  # see testSetCc()

    def testSetBcc(self):
        self.checkSetAddr(self.mail.set_bcc, self.mail.get_bcc)

    def testAddBcc(self):
        self.checkAddAddr(self.mail.add_bcc, self.mail.get_bcc)

    def testGetBcc(self):
        pass  # see testSetBcc()

    def testGetReceipients(self):
        self.mail.set_to('test1')
        self.mail.set_cc('test2')
        self.mail.set_bcc('test3')
        self.assertEqual(self.mail.get_receipients(),
                         ['test1', 'test2', 'test3'])

    def testSetSubject(self):
        self.assertEqual(self.mail.get_subject(), '')
        self.mail.set_subject('test')
        self.assertEqual(self.mail.get_subject(), 'test')

    def testGetSubject(self):
        pass  # see testSetSubject()

    def testSetBody(self):
        self.assertEqual(self.mail.get_body(), '')
        self.mail.set_body('test')
        self.assertEqual(self.mail.get_body(), 'test')

    def testGetBody(self):
        pass  # see testSetBody()

    def testAddAttachment(self):
        self.assertEqual(self.mail.get_attachments(), [])
        self.mail.add_attachment('foo')
        self.assertEqual(self.mail.get_attachments(), ['foo'])
        self.mail.add_attachment('bar')
        self.assertEqual(self.mail.get_attachments(), ['foo', 'bar'])

    def testGetAttachments(self):
        self.testAddAttachment()

    def testGetSmtpHeader(self):
        pass  # see testSetFromTemplateString()

    def testGetSmtpMail(self):
        pass  # see testSetFromTemplateString()


class mailTest(unittest.TestCase):
    CORRELATE = Exscript.util.mail

    def checkResult(self, mail):
        self.assert_(isinstance(mail, Mail))

        # Remove the "From:" line.
        result = mail.get_smtp_mail().split('\n', 1)[1].strip()
        expected = smtp.split('\n', 1)[1].strip()

        # Compare the results.
        for key, value in vars.iteritems():
            expected = expected.replace('{' + key + '}', value)
        self.assertEqual(result, expected)

    def testFromTemplateString(self):
        from Exscript.util.mail import from_template_string
        mail = from_template_string(template, **vars)
        self.checkResult(mail)

    def testFromTemplate(self):
        from Exscript.util.mail import from_template
        tmpfile = tempfile.NamedTemporaryFile()
        tmpfile.write(template)
        tmpfile.flush()
        mail = from_template(tmpfile.name, **vars)
        tmpfile.close()
        self.checkResult(mail)

    def testSend(self):
        pass  # no easy way to test without spamming.


def suite():
    mail_cls = unittest.TestLoader().loadTestsFromTestCase(MailTest)
    mail_module = unittest.TestLoader().loadTestsFromTestCase(mailTest)
    return unittest.TestSuite([mail_cls, mail_module])
if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
