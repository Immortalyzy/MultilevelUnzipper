# MultilevelUnzipper
Unzip multilevel password-protected files, using pre-defined password lists. 
Supports only archives compatible with 7-Zip software. 

Requirements:
Python 3.0+
7-Zip installed

Usage : Unzip the file, click the install.exe, set initial settings and click install. The program will be installed in a folder under AppData folder of the user, and "Unzip all files under this directory" and "Unzip this file" will be added to the user's right-click menu. 
You should store all your passwords in the file .passwords.txt under your home directory. 


WARNING:
1, if you have set "autodeleteexisting" to "True", make sure to move all the existing extracted files (especially games that contain your save files in it) or they will be removed and you will lose your save files PERMANENTLY.
