class MailboxMessage(object):
    def __init__(self, api, message):
        self.id = message['convId']
        self.conv = Conversation(api, self.id)
        self.subject = message['subject']
        self.unread = message['unread']
        self.sticky = message['sticky']
        self.fwd_id = message['forwardedId']
        self.fwd_name = message['forwardedName']
        self.sender_id = message['senderId']
        self.username = message['username']
        self.donor = message['donor']
        self.warned = message['warned']
        self.enabled = message['enabled']
        self.date = message['date']

    def __repr__(self):
        return "MailboxMessage ID %s - %s %s %s" % (self.id, self.subject, self.sender_id, self.username)


class ConversationMessage(object):
    def __init__(self, msg_resp):
        self.id = msg_resp['messageId']
        self.sender_id = msg_resp['senderId']
        self.sender_name = msg_resp['senderName']
        self.sent_date = msg_resp['sentDate']
        self.bb_body = msg_resp['bbBody']
        self.body = msg_resp['body']

    def __repr__(self):
        return "ConversationMessage ID %s - %s %s" % (self.id, self.sender_name, self.sent_date)


class Conversation(object):
    def __init__(self, api, conv_id):
        self.id = conv_id
        self.parent_api = api
        self.subject = None
        self.sticky = None
        self.messages = []

    def __repr__(self):
        return "Conversation ID %s - %s" % (self.id, self.subject)

    def set_conv_data(self, conv_resp):
        assert self.id == conv_resp['convId']
        self.subject = conv_resp['subject']
        self.sticky = conv_resp['sticky']
        self.messages = [ConversationMessage(m) for m in conv_resp['messages']]

    def update_conv_data(self):
        response = self.parent_api.request(action='inbox',
                                           type='viewconv', id=self.id)
        self.set_conv_data(response)


class Mailbox(object):
    """
    This class represents the logged in user's inbox/sentbox
    """
    def __init__(self, parent_api, boxtype='inbox', page='1', sort='unread'):
        self.parent_api = parent_api
        self.boxtype = boxtype
        self.current_page = page
        self.total_pages = None
        self.sort = sort
        self.messages = None

    def set_mbox_data(self, mbox_resp):
        """
        Takes parsed JSON response from 'inbox' action on api
        and updates the available subset of mailbox information.
        """
        self.current_page = mbox_resp['currentPage']
        self.total_pages = mbox_resp['pages']
        self.messages = \
          [MailboxMessage(self.parent_api, m) for m in mbox_resp['messages']]

    def update_mbox_data(self):
        response = self.parent_api.request(action='inbox',
                     type=self.boxtype, page=self.current_page, sort=self.sort)
        self.set_mbox_data(response)

    def next_page(self):
        if not self.total_pages:
            raise ValueError("call update_mbox_data() first")
        total_pages = int(self.total_pages)
        cur_page = int(self.current_page)
        if cur_page < total_pages:
            return Mailbox(self.parent_api, self.boxtype,
                           str(cur_page + 1), self.sort)
        raise ValueError("Already at page %d/%d" % (cur_page, total_pages))

    def prev_page(self):
        if not self.total_pages:
            raise ValueError("call update_mbox_data() first")
        total_pages = int(self.total_pages)
        cur_page = int(self.current_page)
        if cur_page > 1:
            return Mailbox(self.parent_api, self.boxtype,
                           str(cur_page - 1), self.sort)
        raise ValueError("Already at page %d/%d" % (cur_page, total_pages))

    def __repr__(self):
        return "Mailbox: %s %s Page %s/%s" \
                 % (self.boxtype, self.sort,
                    self.current_page, self.total_pages)
