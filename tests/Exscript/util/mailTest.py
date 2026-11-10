import email
import os
import tempfile
import unittest
from getpass import getuser
from unittest import mock

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
        self.assertNotEqual(mail.get_sender(), None)
        self.assertNotEqual(mail.get_sender(), '')
        user = getuser()
        self.assertTrue(mail.get_sender().startswith(user + '@'))

    def testSetFromTemplateString(self):
        self.mail.set_from_template_string(template)
        tmpl = self.mail.get_smtp_mail().strip()
        self.assertEqual(tmpl, smtp)
        head = self.mail.get_smtp_header().strip()
        self.assertTrue(tmpl.startswith(head))

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

    def testGetRecipients(self):
        self.mail.set_to('test1')
        self.mail.set_cc('test2')
        self.mail.set_bcc('test3')
        self.assertEqual(self.mail.get_recipients(), ['test1', 'test2', 'test3'])

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
        self.assertIsInstance(mail, Mail)

        # Remove the "From:" line.
        result = mail.get_smtp_mail().split('\n', 1)[1].strip()
        expected = smtp.split('\n', 1)[1].strip()

        # Compare the results.
        for key, value in vars.items():
            expected = expected.replace('{' + key + '}', value)
        self.assertEqual(result, expected)

    def testFromTemplateString(self):
        from Exscript.util.mail import from_template_string

        mail = from_template_string(template, **vars)
        self.checkResult(mail)

    def testFromTemplate(self):
        from Exscript.util.mail import from_template

        with tempfile.NamedTemporaryFile(
            delete=False
        ) as tmpfile:  # Windows: close before reopening
            tmpfile.write(template.encode('utf8'))
        self.addCleanup(os.remove, tmpfile.name)
        mail = from_template(tmpfile.name, **vars)
        self.checkResult(mail)

    def testSend(self):
        mail = Mail(sender='me@example.com', to='you@example.com', subject='Report', body='Grüße')
        with mock.patch('smtplib.SMTP') as smtp:
            Exscript.util.mail.send(mail, 'mail.example.com')
        smtp.assert_called_once_with('mail.example.com')
        sender, rcpt, text = smtp.return_value.__enter__.return_value.sendmail.call_args.args
        self.assertEqual((sender, rcpt), ('me@example.com', ['you@example.com']))
        message = email.message_from_string(text)
        self.assertEqual(message['Subject'], 'Report')
        self.assertEqual(message.get_payload()[0].get_payload(decode=True), 'Grüße'.encode())
        smtp.return_value.__exit__.assert_called_once()  # QUIT, and the connection is closed

    def testSendDoesNotConnectIfTheMailIsIncomplete(self):
        mail = Mail(to='you@example.com')
        mail.add_attachment(os.path.join(tempfile.gettempdir(), 'missing-attachment'))
        with mock.patch('smtplib.SMTP') as smtp:
            self.assertRaises(OSError, Exscript.util.mail.send, mail)
        smtp.assert_not_called()


def suite():
    mail_cls = unittest.TestLoader().loadTestsFromTestCase(MailTest)
    mail_module = unittest.TestLoader().loadTestsFromTestCase(mailTest)
    return unittest.TestSuite([mail_cls, mail_module])


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
