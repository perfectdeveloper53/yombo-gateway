"""
Extends the web_interface library class to add support for building the static files for web clients.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/webinterface/class_helpers/builddist.html>`_
"""
# Import python libraries
import json
from os import environ, path, makedirs, listdir, walk as oswalk, unlink, stat as osstat, kill
from PIL import Image
import shutil
from time import time

# Import twisted libraries
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, DeferredList
from twisted.internet.utils import getProcessOutput

# Import Yombo libraries
from yombo.utils import read_file, download_file
from yombo.utils.networking import ip_addres_in_local_network
from yombo.core.log import get_logger
from yombo.utils.filewriter import FileWriter
logger = get_logger("library.webinterface.class_helpers.builddist")


class BuildDistribution:
    """
    Handles building the distribution files. Primarily, it runs the NPM Build process and copies the contents
    to the working_dir where it can be accessed through the web server.
    """
    @inlineCallbacks
    def build_dist(self, verbose=None):
        """
        This builds the ~/.yombo/frontend folder.

        1) Copies the basic webinterface items to ~/.yombo/frontend for us when the user
           isn't logged in, or when the gateawy needs to be setup

        2) Generates the frontend single page application, and copies to ~/.yombo/frontend
           This step uses NPM to build the application and take a few minutes on low end
           devices such as Raspberry PI.

        3) Checks if there's any nice background images, if not, it downloads some free ones
           and renders various sizes to be displayed as needed.
        :return:
        """
        filename = f"{self.app_dir}/yombo/frontend/static/nuxt.env"
        file_out = FileWriter(filename=filename, mode="w")  # open in append mode.
        file_out.write(self.nuxt_env_content())
        yield file_out.close_while_waiting()

        if verbose is True:
            logger.info("Copying web static content.")
        yield self.copy_static_web_items()
        if not path.exists(self.working_dir + "/frontend/img/bg/5.jpg"):
            if verbose is True:
                logger.info("Downloading pretty background images.")
            yield self.download_background_images()
        if not path.exists(f"{self.working_dir}/frontend/_nuxt"):
            if verbose is True:
                logger.info("Copying basic web items for setup wizard.")
            yield self.copy_frontend()  # We copy the previously built frontend in case it's new install..
        yield self.build_frontend()

    @inlineCallbacks
    def frontend_npm_run(self, arguments=None):
        """
        Does the actual execution of the npm run.

        :param arguments: A list of arguments to pass to NPM.
        :return:
        """
        if arguments is None:
            arguments = ["npm", "run", "build", "--", self.working_dir]

        results = yield getProcessOutput(
            "nice",
            arguments,
            path=f"{self.app_dir}/yombo/frontend",
            env=environ.copy(),
            errortoo=True,
        )
        self.npm_build_results = results

    @inlineCallbacks
    def build_frontend(self, environemnt=None):
        """
        This execute the NPM build process for the frontend.

        :return:
        """
        if self.frontend_building is True:
            return

        if self.frontend_building is True:
            logger.warn("Cannot build frontend : already building...")
            return
        start_time = time()

        # Idea #8953872 - Only build if the files have changed. This will generate a sha1 for an entire directory.
        # find ./ ! -path "./node_modules/*" ! -path "./dist/*" -type f -print0 | sort -z | xargs -0 sha1sum | sha1sum

        npm_running = yield self.check_npm_running()
        if npm_running:
            logger.info("Frontend builder appears to already be running. Won't build now.")
            return

        logger.warn("Web Frontend: Starting build. This may take a while to complete. Will notify when done.")
        self.frontend_building = True
        yield self.frontend_npm_run()  # THe build script copies to the final destination.
        logger.warn("Web Frontend: Finished building in {seconds} seconds. Ready to use.", seconds=round(time() - start_time))

        self.display_how_to_access()
        self.frontend_building = False

    @inlineCallbacks
    def check_npm_running(self):
        """
        Checks if the builder process is running. First, it checks if the PID file is found. It then
        inspects that file and checks to make sure the actual process is running. If the process is running,
        return True. If not, remove file the PID file and return False.
        :return:
        """
        # Check if builder is already running:
        if path.isfile(f"{self.app_dir}/yombo/frontend/util/builder.pid") is False:
            return False

        pid = yield read_file(f"{self.app_dir}/yombo/frontend/util/builder.pid")
        try:
            kill(int(pid), 0)
            return True
        except OSError:
            unlink(f"{self.app_dir}/yombo/frontend/util/builder.pid")
            return False

    @inlineCallbacks
    def copy_frontend(self, environemnt=None):
        """
        Copy the frontend contents to the static folder.
        :return:
        """
        yield threads.deferToThread(self.empty_directory, f"{self.working_dir}/frontend/_nuxt")
        if path.exists(f"{self.app_dir }/yombo/frontend/dist/_nuxt/"):
            yield self.copytree("yombo/frontend/dist/_nuxt/", "frontend/_nuxt/")
        if path.exists(f"{self.app_dir }/yombo/frontend/dist/index.html"):
            yield threads.deferToThread(shutil.copy2, self.app_dir + "/yombo/frontend/dist/index.html", self.working_dir + "/frontend/")
        if path.exists(f"{self.app_dir }/yombo/frontend/dist/sw.js"):
            yield threads.deferToThread(shutil.copy2, self.app_dir + "/yombo/frontend/dist/sw.js", self.working_dir + "/frontend/")

    @inlineCallbacks
    def download_background_images(self):
        """
        Downloads background images for various web pages. This downloads free images,
        and prepares various sizes.
        :return:
        """
        # print("!@!@!@!@!@ Download images...")

        background_images = [  # these images are free.  See unplash.com
            "https://images.unsplash.com/photo-1414490929659-9a12b7e31907",
            "https://images.unsplash.com/reserve/unsplash_524010c76b52a_1.JPG",
            "https://images.unsplash.com/reserve/z7R1rjT6RhmZdqWbM5hg_R0001139.jpg",
            "https://images.unsplash.com/reserve/J3URHssSQyqifuJVcgKu_Wald.jpg",
            "https://images.unsplash.com/uploads/14114036359651bd991f1/b3ed8fdf",
            "https://images.unsplash.com/reserve/vof4H8A1S02iWcK6mSAd_sarahmachtsachen.com_TheBeach.jpg",
            ]  # If added/updated, update WI/route/user.py - page_usr_login_user_get
        if not path.exists(f"{self.working_dir}/frontend/img/bg"):
            makedirs(f"{self.working_dir}/frontend/img/bg")

        for idx, image in enumerate(background_images):
            logger.debug(f"WebInterface background image: {image}")
            try:
                yield download_file(image, f"{self.working_dir}/frontend/img/bg/{idx}.jpg")
            except:
                continue
            logger.debug(f"WebInterface background image, done: {image}")
            full = Image.open(f"{self.working_dir}/frontend/img/bg/{idx}.jpg")
            sizes = {
                2048: 67,
                1364: 67,
                600: 65,
            }
            for size, quality in sizes.items():
                out = yield threads.deferToThread(full.resize, (size, size), Image.BICUBIC)
                yield threads.deferToThread(out.save,
                                            f"{self.working_dir}/frontend/img/bg/{idx}_{size}.jpg",
                                            format="JPEG",
                                            subsampling=0,
                                            quality=quality)

    def nuxt_env_content(self, request=None):
        internal_http_port = self._Gateways.local.internal_http_port
        internal_http_secure_port = self._Gateways.local.internal_http_secure_port
        external_http_port = self._Gateways.local.external_http_port
        external_http_secure_port = self._Gateways.local.external_http_secure_port
        internal_http_port = internal_http_port if internal_http_port is not None else \
            self._Configs.get("self", "nonsecure_port", None, False)
        internal_http_secure_port = internal_http_secure_port if internal_http_secure_port is not None else \
            self._Configs.get("self", "secure_port", None, False)
        external_http_port = external_http_port if external_http_port is not None else \
            self._Configs.get("self", "nonsecure_port", None, False)
        external_http_secure_port = external_http_secure_port if external_http_secure_port is not None else \
            self._Configs.get("self", "secure_port", None, False)

        client_location = "local"
        if request is not None and ip_addres_in_local_network(request.getClientIP()):
            client_location = "remote"

        return json.dumps({
            "gateway_id": self.gateway_id,
            "working_dir": self.working_dir,
            "internal_http_port": internal_http_port,
            "internal_http_secure_port": internal_http_secure_port,
            "external_http_port": external_http_port,
            "external_http_secure_port": external_http_secure_port,
            "api_key": self._Configs.get("frontend", "api_key",
                                         "4Pz5CwKQCsexQaeUvhJnWAFO6TRa9SafnpAQfAApqy9fsdHTLXZ762yCZOct", False),
            "mqtt_port": self._MQTT.server_listen_port,
            "mqtt_port_ssl": self._MQTT.server_listen_port_ss_ssl,
            "mqtt_port_websockets": self._MQTT.server_listen_port_websockets,
            "mqtt_port_websockets_ssl": self._MQTT.server_listen_port_websockets_ss_ssl,
            "client_location": client_location,
            "static_data": False,
        }, indent='\t', separators=(',', ': '))

    @inlineCallbacks
    def copy_static_web_items(self):
        """
        Copies base webpages, not relating to the frontend application.

        :return:
        """
        def do_cat(inputs, output):
            output = f"{self.working_dir}/frontend/{output}"
            makedirs(path.dirname(output), exist_ok=True)
            with open(output, "w") as outfile:
                for fname in inputs:
                    fname = "yombo/lib/webinterface/static/" + fname
                    with open(fname) as infile:
                        outfile.write(infile.read())

        CAT_SCRIPTS = [
            "source/bootstrap4/css/bootstrap.min.css",
            "source/bootstrap-select/css/bootstrap-select.min.css",
            "source/bootstrap4-toggle/bootstrap4-toggle.min.css",
            "source/yombo/yombo.css",
            "source/yombo/mappicker.css",
        ]
        CAT_SCRIPTS_OUT = "css/basic_app.min.css"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/yombo/mappicker.js",
            ]
        CAT_SCRIPTS_OUT = "js/mappicker.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/jquery/jquery.validate.min.js",
        ]
        CAT_SCRIPTS_OUT = "js/jquery.validate.min.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        CAT_SCRIPTS = [
            "source/jquery/jquery-3.3.1.min.js",
            "source/jquery/jquery.validate.min.js",
            "source/js-cookie/js.cookie.min.js",
            "source/bootstrap4/js/bootstrap.bundle.min.js",
            "source/bootstrap-select/js/bootstrap-select.min.js",
            "source/yombo/jquery.are-you-sure.js",
            "source/bootstrap4-toggle/bootstrap4-toggle.min.js",
            "source/yombo/yombo.js",
        ]
        CAT_SCRIPTS_OUT = "js/basic_app.js"
        do_cat(CAT_SCRIPTS, CAT_SCRIPTS_OUT)

        filename = f"{self.working_dir}/frontend/nuxt.env"
        file_out = FileWriter(filename=filename, mode="w")  # open in append mode.
        file_out.write(self.nuxt_env_content())
        yield file_out.close_while_waiting()

        yield self.copytree("yombo/lib/webinterface/static/source/img/", "frontend/img/")

    @inlineCallbacks
    def copytree(self, src, dst, symlinks=False, ignore=None):
        if src.startswith("/") is False:
            src = self.app_dir + "/" + src
        if dst.startswith("/") is False:
            dst = self.working_dir + "/" + dst

        if not path.exists(dst):
            makedirs(dst)
        for item in listdir(src):
            s = path.join(src, item)
            d = path.join(dst, item)
            if path.isdir(s):
                self.copytree(s, d, symlinks, ignore)
            else:
                if not path.exists(d) or osstat(s).st_mtime - osstat(d).st_mtime > 1:
                    yield threads.deferToThread(shutil.copy2, s, d)

    def empty_directory(self, delpath):
        for root, dirs, files in oswalk(delpath):
            for f in files:
                unlink(path.join(root, f))
            for d in dirs:
                shutil.rmtree(path.join(root, d))