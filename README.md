#IPyXMPP

##### IPyXMPP is a chat bot serving an IPython shell over XMPP.

You can run IPython commands and see output plots just by chatting with the jabber id you configured IPyXMPP to use: no need for knowing hostnames or setting up ssh tunnels.

It has been developed as a component for a tool (to be released soon) for interacting in real time with the data being processed in some simulation codes. The tool will embed an IPython shell in C simulation codes and use its extraordinary features for real time data analysis. This XMPP bot has been written to provide the easiest possible access to the simplest commands.

![Image](doc/shot1.png?raw=true)

### Dependencies & Usage:

pip install -r requirements.txt

python bot.py --jid=\[your jabber id\] --password=\[<XMPP password\]  --passphrase=\[Passphrase for running commands\]

### Supported clients:

All native and web-based XMPP clients can be used to chat with the IPython bot, but in order to see plot images in the chat window, you need a client supporting XEP-0231 (Adium, ...). The maximum size of images is determined by the max stanza size supported by your XMPP server.


### TODOs:

- Multiple ipython kernels, at least one per chat peer.
- Plot visualization for clients without XEP-0231 (google talk, etc.).
- Improve code quality and tests (currently: hackaton-level code quality).
- Encryption?
