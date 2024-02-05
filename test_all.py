""" general test """
import MultilevelUnzipper as uz

uz.read_settings()
uz.settings["autodelete"] = True
uz.settings["automoveup"] = True


# target folder
target = "./test/test_folder/"
uz.main(target=target)
