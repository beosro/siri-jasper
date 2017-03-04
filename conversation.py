# -*- coding: utf-8-*-
import logging
import RPi.GPIO as GPIO
from notifier import Notifier
from brain import Brain
import time
import imaplib
import email
import thread

global username
global password

#############################################

# Fill in your username and password below
username = 'your username'
password = 'your password'

#############################################


class Conversation(object):

    def __init__(self, persona, mic, profile):
        self._logger = logging.getLogger(__name__)
        self.persona = persona
        self.mic = mic
        self.profile = profile
        self.brain = Brain(mic, profile)
        self.notifier = Notifier(profile)

    global last_checked
    last_checked = -1

    def fetch_siri_command(self,mail):
        global last_checked
        mail.list()
        mail.select("Notes")
        result, uidlist = mail.search(None, "ALL")
        latest_email_id = uidlist[0].split()[-1]
        if latest_email_id == last_checked:
            return
        last_checked = latest_email_id
        result, data = mail.fetch(latest_email_id, "(RFC822)")
        voice_command = email.message_from_string(data[0][1].decode('utf-8'))
        c = str(voice_command.get_payload()).lower().strip()
        return c

    def main(self):
        global username
        global password
        x = 0
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(username, password)
        self.fetch_siri_command(mail)
        x = 1
        while x:
            try:
                c = str(self.fetch_siri_command(mail))
                if c != "None":
                    print("You said " + c)
                    self.brain.query(c,"siri")
            except Exception as exc:
                print("Received an exception while running: {exc}"
                      "\nRestarting...".format(**locals()))
            time.sleep(1)

    def handleForever(self):
        """
        Delegates user input to the handling function when activated.
        """
        self._logger.info("Starting to handle conversation with keyword '%s'.",
                          self.persona)
        thread.start_new_thread(self.main,())
        while True:
            # Print notifications until empty
            notifications = self.notifier.getAllNotifications()
            for notif in notifications:
                self._logger.info("Received notification: '%s'", str(notif))

            self._logger.debug("Started listening for keyword '%s'",
                               self.persona)
            

            threshold, transcribed = self.mic.passiveListen(self.persona)
            self._logger.debug("Stopped listening for keyword '%s'",
                               self.persona)

            if not transcribed or not threshold:
                self._logger.info("Nothing has been said or transcribed.")
                continue
            self._logger.info("Keyword '%s' has been said!", self.persona)
      
            self._logger.debug("Started to listen actively with threshold: %r",
                               threshold)
            input = self.mic.activeListenToAllOptions(threshold)

            self._logger.debug("Stopped to listen actively with threshold: %r",
                               threshold)

            if input:
                self.brain.query(input,"stt")
            else:
                self.mic.say("Pardon?")
