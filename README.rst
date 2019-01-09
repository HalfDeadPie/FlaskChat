FlaskChat
==================
Semestral work - (MI-DSV)
**************************

Flaskchat is an application, which provides distributed chat for multiple users. The application uses a leader
to provide time synchronisation of regular messages. Chang and Roberts algorithm is used for election of the
leader. This is a semestral work for subject MI-DSV at CTU in Prague. The communication between nodes
is implemented using requests and and every node of a chat is Flask server.

Instalation
################################

    First, you need to clone this repository::

            git clone https://github.com/HalfDeadPie/FlaskChat

    Then you can install it using pip::

            pip install FlaskChat/

Usage
################################

    To run the Flaskchat application, you need to write a command::

        flaskchat [OPTIONS] IPPORT FRIEND

    - **OPTIONS**
        may be **-d/--debug** for debug logging
    - **IPPORT**
        is your IP address and port for Flask server, use formatting **ip:port**
    - **FRIEND**
        is  IP address and port for Flask server of a friend, who uses FlaskChat. Your friend
        may be alone or joined in chatgroup already. Use formatting **ip:port**

    - Example::

            flaskchat 192.168.122.1:5001 192.168.122.9:5009 -d


Testing
################################
Application has been tested on 5 virtual machines (Kali Linux).

