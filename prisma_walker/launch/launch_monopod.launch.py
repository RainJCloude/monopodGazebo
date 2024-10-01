from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import os
from ament_index_python.packages import get_package_share_directory
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessExit

def generate_launch_description():
    declared_arguments = []
    # UR specific arguments

    declared_arguments.append(
        DeclareLaunchArgument(
            "rviz_config_file", #this will be the name of the argument  
            default_value=PathJoinSubstitution(
                [FindPackageShare("prisma_walker"), "config", "rviz", "standing.rviz"]
            ),
            description="RViz config file (absolute path) to use when launching rviz.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "frame_prefix",
            default_value='""',
            description="Prefix of the joint names, useful for "
            "multi-robot setup. If changed than also joint names in the controllers' configuration "
            "have to be updated.",
        )
    )

    urdf_path = os.path.join(
        get_package_share_directory('prisma_walker'), "urdf", "prisma_walker.urdf"
    )
    with open(urdf_path, 'r') as infp:
        robot_desc = infp.read()
    

    # This is the most important part to pass arguments to a launch file. 
    #LaunchConfiguration is used to read the launch arguments. In this way, when you call the launch file you can pass arguments
    description_file = LaunchConfiguration("description_file") #this is the path
    frame_prefix = LaunchConfiguration("frame_prefix")
    #rviz_config_file = LaunchConfiguration("rviz_config_file")

    #get_package_share_directory and FindPackageShare seems to be the same thing
    rviz_config = os.path.join(
        get_package_share_directory('prisma_walker'), "config", "rviz", "standing.rviz"
    )

    robot_description = {"robot_description": robot_desc} #this wants the string with the whole content, not the path to the file. It is a parameter


    joint_state_publisher_node = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description,
                {"use_sim_time": True}
            ], #parameters are different from arguments. They must be a list of dictionary.ù
        remappings=[('/robot_description', '/robot_description')]
    )

    #Robot-state-publisher e joint-state-publisher potrebbero dover essere installati

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config], #This is an argument, and must be a path
    )


    declared_arguments.append(DeclareLaunchArgument('gz_args', default_value='-r -v 1 empty.sdf',
                              description='Arguments for gz_sim'),)
    
    gazebo_ignition = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [PathJoinSubstitution([FindPackageShare('ros_gz_sim'),
                                    'launch',
                                    'gz_sim.launch.py'])]), #ign_gazebo.launch.py
            launch_arguments={'gz_args': LaunchConfiguration('gz_args')}.items()
    )

    position = [0.0, 0.0, 0.0]

    gz_spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-topic', 'robot_description', #spawn what there is in the topic robot_description. Alternatively yoiu can use -file
                   '-name', 'prisma_walker',
                   '-allow_renaming', 'true',
                    "-x", str(position[0]),
                    "-y", str(position[1]),
                    "-z", str(position[2]),],
    )
 




    
    robot_controllers = PathJoinSubstitution([FindPackageShare("prisma_walker"), "config", "pos_controller.yaml",])

    #Controller manager load the controllers defined in the yaml file
    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node", 
        name='controller_manager',
        parameters=[robot_controllers],
        output="both",
        remappings=[
            ("~/robot_description", "/robot_description"),
        ],
    )

    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    ) #among the controller of controller_manager you are saying to launchg the joint_state_broadcaster

    joint_trajectory_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_trajectory_controller", "--controller-manager", "/controller_manager", "--controller-manager-timeout", "20"], #-c means name of the controller-manager
    ) 

    """delay_joint_traj_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_sensor,
            on_exit=[joint_trajectory_controller],
        )
    )

    delay_joint_state_broadcaster = (
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=spawn_sensor,
                on_exit=[joint_state_broadcaster],
            )
        )
    )"""
 


  
    nodes_to_start = [
        joint_state_publisher_node,
        robot_state_publisher_node, #publish pose of each link and transformation to know ehre the robot is
        rviz_node,
        gazebo_ignition,
        gz_spawn_entity,
        #control_node, #if your hardware interface is the simulator, the ros-control will be the one specified in the plugin gazebo, 
        #joint_trajectory_controller,
        #joint_state_broadcaster, #publish the state of the robot as sensor-masgs for control (like the joints pos e vel)
        #delay_joint_traj_controller, #ros controller chosen. I could also use a psition controller
        #delay_joint_state_broadcaster,
    ]
    
    """In rviz, quando selezioni il modello, devi mettere il topic /robot_descriptio in Description topic"""

    return LaunchDescription(declared_arguments + nodes_to_start) #its argument must to be a list