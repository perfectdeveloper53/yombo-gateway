# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the pause handling for /scenes sub directory.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.17.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/scenes.py>`_
"""
# from collections import OrderedDict
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.scenes.pause")


def route_scenes_pause(webapp):
    with webapp.subroute("/scenes") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/scenes/index", "Scenes")

        @webapp.route('/<string:scene_id>/add_pause', methods=['GET'])
        @require_auth()
        def page_scenes_item_pause_add_get(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'item_type': 'pause',
                'duration': webinterface.request_get_default(request, 'duration', 5),
                'weight': webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_item(scene_id)) + 1) * 10),
            }
            try:
                data['duration'] = float(data['duration'])
            except Exception as e:
                webinterface.add_alert("Duration must be an integer or float.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_pause(webinterface, request, session, scene, data, 'add', "Add a pause to scene")

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/add_pause" % scene_id, "Add Item: Pause")
            return page_scenes_form_pause(webinterface, request, session, scene, data, 'add', "Add a pause to scene")

        @webapp.route('/<string:scene_id>/add_pause', methods=['POST'])
        @require_auth()
        def page_scenes_item_pause_add_post(webinterface, request, session, scene_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'item_type': 'pause',
                'duration': webinterface.request_get_default(request, 'duration', 5),
                'weight': webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_item(scene_id)) + 1) * 10),
            }
            try:
                data['duration'] = float(data['duration'])
            except Exception as e:
                webinterface.add_alert("Duration must be an integer or float.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_pause(webinterface, request, session, scene, data, 'add', "Add a pause to scene")

            try:
                webinterface._Scenes.add_scene_item(scene_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot add pause to scene. %s" % e.message, 'warning')
                return page_scenes_form_pause(webinterface, request, session, scene, data, 'add', "Add a pause to scene")

            webinterface.add_alert("Added pause item to scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        @webapp.route('/<string:scene_id>/edit_pause/<string:item_id>', methods=['GET'])
        @require_auth()
        def page_scenes_item_pause_edit_get(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                item = webinterface._Scenes.get_item(scene_id, item_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for scene doesn't exist.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene.scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/edit_pause" % scene.scene_id, "Edit item: Pause")
            return page_scenes_form_pause(webinterface, request, session, scene, item, 'edit',
                                              "Edit scene item: State")

        @webapp.route('/<string:scene_id>/edit_pause/<string:item_id>', methods=['POST'])
        @require_auth()
        def page_scenes_item_pause_edit_post(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene could not be located.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            data = {
                'item_type': 'pause',
                'duration': webinterface.request_get_default(request, 'duration', 5),
                'weight': webinterface.request_get_default(
                    request, 'weight', (len(webinterface._Scenes.get_item(scene_id)) + 1) * 10),
            }
            try:
                data['duration'] = float(data['duration'])
            except Exception as e:
                webinterface.add_alert("Duration must be an integer or float.", 'warning')
                return webinterface.redirect(request, '/scenes/%s/details' % scene_id)

            try:
                data['weight'] = int(data['weight'])
            except Exception:
                webinterface.add_alert('Must enter a number for a weight.', 'warning')
                return page_scenes_form_pause(webinterface, request, session, scene, data, 'add', "Add a pause to scene")

            try:
                webinterface._Scenes.edit_scene_item(scene_id, item_id, **data)
            except YomboWarning as e:
                webinterface.add_alert("Cannot edit pause within scene. %s" % e.message, 'warning')
                return page_scenes_form_pause(webinterface, request, session, scene, data, 'add',
                                              "Edit scene item: Pause")

            webinterface.add_alert("Edited a pause item for scene '%s'." % scene.label)
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)

        def page_scenes_form_pause(webinterface, request, session, scene, data, action_type, header_label):
            page = webinterface.get_template(request, webinterface._dir + 'pages/scenes/form_pause.html')

            return page.render(alerts=webinterface.get_alerts(),
                               header_label=header_label,
                               scene=scene,
                               data=data,
                               action_type=action_type,
                               )

        @webapp.route('/<string:scene_id>/delete_pause/<string:item_id>', methods=['GET'])
        @require_auth()
        def page_scenes_item_pause_delete_get(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                item = webinterface._Scenes.get_item(scene_id, item_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for scene doesn't exist.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            page = webinterface.get_template(
                request,
                webinterface._dir + 'pages/scenes/delete_pause.html'
            )
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/scenes/%s/details" % scene_id, scene.label)
            webinterface.add_breadcrumb(request, "/scenes/%s/delete_pause" % scene_id, "Delete item: Pause")
            return page.render(alerts=webinterface.get_alerts(),
                               scene=scene,
                               item=item,
                               item_id=item_id,
                               )

        @webapp.route('/<string:scene_id>/delete_pause/<string:item_id>', methods=['POST'])
        @require_auth()
        def page_scenes_item_pause_delete_post(webinterface, request, session, scene_id, item_id):
            try:
                scene = webinterface._Scenes[scene_id]
            except KeyError as e:
                webinterface.add_alert("Requested scene doesn't exist: %s" % scene_id, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                item = webinterface._Scenes.get_item(scene_id, item_id)
            except KeyError as e:
                webinterface.add_alert("Requested item for scene doesn't exist.", 'warning')
                return webinterface.redirect(request, '/scenes/index')

            try:
                confirm = request.args.get('confirm')[0]
            except:
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the pause from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_pause/%s' % (scene_id, item_id))

            if confirm != "delete":
                webinterface.add_alert('Must enter "delete" in the confirmation box to '
                                       'delete the pause from the scene.', 'warning')
                return webinterface.redirect(request,
                                             '/scenes/%s/delete_pause/%s' % (scene_id, item_id))

            try:
                webinterface._Scenes.delete_scene_item(scene_id, item_id)
            except YomboWarning as e:
                webinterface.add_alert("Cannot delete pause from scene. %s" % e.message, 'warning')
                return webinterface.redirect(request, '/scenes/index')

            webinterface.add_alert("Deleted pause item for scene.")
            return webinterface.redirect(request, "/scenes/%s/details" % scene.scene_id)