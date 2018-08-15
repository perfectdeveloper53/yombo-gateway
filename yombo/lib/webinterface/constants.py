NAV_SIDE_MENU = [
    {
        'label1': 'Panel',
        'label2': 'Panel',
        'priority1': 200,
        'priority2': 500,
        'icon': 'fa fa-gamepad fa-fw',
        'url': '/panel/index',
        'tooltip': 'System Panel',
        'opmode': 'run',
        'cluster': 'master',
    },
    {
        'label1': 'Devices',
        'label2': 'Devices',
        'priority1': 400,
        'priority2': 500,
        'icon': 'fa fa-wifi fa-fw',
        'url': '/devices/index',
        'tooltip': 'Show Devices',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'Discovery',
        'label2': 'Discovery',
        'priority1': 450,
        'priority2': 450,
        'icon': 'fa fa-hand-holding fa-fw',
        'url': '/discovery/index',
        'tooltip': 'Auto discovered devices',
        'opmode': 'run',
        'cluster': 'any',
    },

    {
        'label1': 'Automation',
        'label2': 'Rules',
        'priority1': 600,
        'priority2': 500,
        'icon': 'fa fa-random fa-fw',
        'url': '/automation/index',
        'tooltip': 'Show Rules',
        'opmode': 'run',
        'cluster': 'any',
    },

    {
        'label1': 'Scenes',
        'label2': 'Scenes',
        'priority1': 700,
        'priority2': 700,
        'icon': 'fa fa-tree fa-fw',
        'url': '/scenes/index',
        'tooltip': 'Control multiple items within a single scene.',
        'opmode': 'run',
        'cluster': 'any',
    },

    {
        'label1': 'Modules',
        'label2': 'Modules',
        'priority1': 800,
        'priority2': 500,
        'icon': 'fa fa-puzzle-piece fa-fw',
        'url': '/modules/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },

    {
        'label1': 'Info',
        'label2': 'Atoms',
        'priority1': 1000,
        'priority2': 2000,
        'icon': 'fa fa-info fa-fw',
        'url': '/atoms/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'Info',
        'label2': 'Device Commands',
        'priority1': 1000,
        'priority2': 3000,
        'icon': 'fa fa-info fa-fw',
        'url': '/devices/device_commands',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },

    {
        'label1': 'Info',
        'label2': 'States',
        'priority1': 1000,
        'priority2': 4000,
        'icon': 'fa fa-info fa-fw',
        'url': '/states/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'Info',
        'label2': 'Voice Commands',
        'priority1': 1000,
        'priority2': 5000,
        'icon': 'fa fa-info fa-fw',
        'url': '/voicecmds/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },

    {
        'label1': 'Statistics',
        'label2': 'General',
        'priority1': 2000,
        'priority2': 500,
        'icon': 'fa fa-chart-line fa-fw',
        'url': '/statistics/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },

    {
        'label1': 'System Settings',
        'label2': 'Basic Settings',
        'priority1': 3500,
        'priority2': 500,
        'icon': 'fa fa-cog fa-fw',
        'url': '/configs/basic',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'System Settings',
        'label2': 'Locations',
        'priority1': 3500,
        'priority2': 750,
        'icon': 'fa fa-cog fa-fw',
        'url': '/locations/index',
        'tooltip': 'Show Locations',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'System Settings',
        'label2': 'Auth Keys',
        'priority1': 3500,
        'priority2': 1000,
        'icon': 'fa fa-cog fa-fw',
        'url': '/authkeys/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'System Settings',
        'label2': 'Users',
        'priority1': 3500,
        'priority2': 1500,
        'icon': 'fa fa-cogs fa-fw',
        'url': '/users/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'System Settings',
        'label2': 'Roles',
        'priority1': 3500,
        'priority2': 2000,
        'icon': 'fa fa-cogs fa-fw',
        'url': '/roles/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'System Settings',
        'label2': 'DNS',
        'priority1': 3500,
        'priority2': 2500,
        'icon': 'fa fa-cogs fa-fw',
        'url': '/configs/dns',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'System Settings',
        'label2': 'Encryption Keys',
        'priority1': 3500,
        'priority2': 3000,
        'icon': 'fa fa-wrench fa-fw',
        'url': '/configs/gpg/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'System Settings',
        'label2': 'Gateways',
        'priority1': 3500,
        'priority2': 4000,
        'icon': 'fa fa-cogs fa-fw',
        'url': '/gateways/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'System Settings',
        'label2': 'Yombo.Ini',
        'priority1': 3500,
        'priority2': 4500,
        'icon': 'fa fa-wrench fa-fw',
        'url': '/configs/yombo_ini',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'Developer Tools',
        'label2': 'Config Tools',
        'priority1': 5000,
        'priority2': 500,
        'icon': 'fa fa-code fa-fw',
        'url': '/devtools/config/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },

    {
        'label1': 'System',
        'label2': 'Backup',
        'priority1': 6000,
        'priority2': 1000,
        'icon': 'fa fa-download fa-fw',
        'url': '/system/backup',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'System',
        'label2': 'Control',
        'priority1': 6000,
        'priority2': 2000,
        'icon': 'fa fa-hdd fa-fw',
        'url': '/system/control',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'System',
        'label2': 'Debug',
        'priority1': 6000,
        'priority2': 3000,
        'icon': 'fa fa-code fa-fw',
        'url': '/devtools/debug/index',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
    {
        'label1': 'System',
        'label2': 'Status',
        'priority1': 6000,
        'priority2': 4000,
        'icon': 'fa fa-hdd fa-fw',
        'url': '/system/status',
        'tooltip': '',
        'opmode': 'run',
        'cluster': 'any',
    },
]

DEFAULT_NODE = [
    {
        'machine_label': 'main_page',
        'node_type': 'webinterface_page',
        'data_type': 'text',
        'data': 'no data yet....',
        'destination': 'gw',
        'children': [
            {
                'machine_label': 'some_item',
                'node_type': 'webinterface_page_item',
                'data_type': 'text',
                'data': 'no data yet.... for item',
                'destination': 'gw',
            },
        ],
    },
]


NOTIFICATION_PRIORITY_MAP_CSS = {
    'debug': 'info',
    'low': 'info',
    'normal': 'info',
    'high': 'warning',
    'urent': 'danger',
}