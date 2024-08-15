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
            "description_file",
            default_value=PathJoinSubstitution(
                [FindPackageShare("anymal_d_simple_description"), "urdf", "anymal.urdf"]
            ),
            description="URDF description file (absolute path) with the robot.",
        )
    )
    declared_arguments.append(
        DeclareLaunchArgument(
            "rviz_config_file", #this will be the name of the argument  
            default_value=PathJoinSubstitution(
                [FindPackageShare("anymal_d_simple_description"), "config", "rviz", "standing.rviz"]
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
    
    declared_arguments.append(DeclareLaunchArgument('gz_args', default_value='-r -v 4 empty.sdf',
                              description='Arguments for gz_sim'),)


    """the robot_desc argument must be a string containing the urdf file.
    Do not confuse with arguments that require paths to the file. 
        -Robot state publisher need as string the whole content of the urdf
        -Rvizw and spawnRobot.py require the paths to their files"""
    urdf_path = os.path.join(
        get_package_share_directory('anymal_d_simple_description'), "urdf", "anymal.urdf"
    )
    with open(urdf_path, 'r') as infp:
        robot_desc = infp.read()
    

    # This is the most important part to pass arguments to a launch file. 
    #LaunchConfiguration is used to read the launch arguments. In this way, when you call the launch file you can pass arguments
    description_file = LaunchConfiguration("description_file") #this is the path
    frame_prefix = LaunchConfiguration("frame_prefix")
    rviz_config_file = LaunchConfiguration("rviz_config_file")

    #get_package_share_directory and FindPackageShare seems to be the same thing
    rviz_config_file = os.path.join(
        get_package_share_directory('anymal_d_simple_description'), "config", "rviz", "standing.rviz"
    )

    robot_description = {"robot_description": robot_desc} #this wants the string with the whole content, not the path to the file. It is a parameter


    joint_state_publisher_node = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
    )

    """Installa il joint-state-publisher
    Runnalo, altrimenti il robot-state-publisher non ha informazioni sui giunti attuati.
    Senza il joint state publisher il tf_tree non vedeva nessun link con i revolute joints, quindi 
    il tf_tree era praticamente un accozzaglia di link, collegati ad altri link solo tramite giunti fissi."""

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[
                {"robot_description": robot_desc},
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
        arguments=["-d", rviz_config_file], #This is an argument, and must be a path
    )

    
    """launch other launch file requires 2 arguments:
        -PythonLaunchDescriptionSource method. it needs the path to the other launch file
        -launch_arguments: a dict of arguments for the launch file. Remember that if a launch file accepts
        parameters is beacuse these parameters have been declared in that launch file as LaunchConfiguration"""
    
    #GAZEBO CLASSIC
    gazebo_classic = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([FindPackageShare("gazebo_ros"), "/launch", "/gazebo.launch.py"]),
        launch_arguments={"gui": "True", 'paused': 'False'}.items(),
    )
    position = [0.0, 0.0, 0.65]
    # Spawn robot. Each argument passed must be a string
    gazeboClassic_spawn_robot = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        name="spawn_entity",
        arguments=["-entity", "nome_che_piace_a_me", #arguments must always be string because strings are the argument passed by cli
                    "-x", str(position[0]),
                    "-y", str(position[1]),
                    "-z", str(position[2]),
                    '-topic', 'robot_description'],
        output="screen", #-file needs the path, not the string
    )
    """invece di passare il file --file percorso_all'_urdf, gli dico direttamente che deve spawnare il robot
    che sta nel topic /robot_description che ha riempito il robot-state-publisher"""



    #IGNITION
    gazebo_ignition = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                [PathJoinSubstitution([FindPackageShare('ros_gz_sim'),
                                    'launch',
                                    'gz_sim.launch.py'])]),
            launch_arguments={'gz_args': LaunchConfiguration('gz_args')}.items()
    )
    gz_spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-topic', 'robot_description',
                   '-name', 'anymal_d',
                   '-allow_renaming', 'true',
                    "-x", str(position[0]),
                    "-y", str(position[1]),
                    "-z", str(position[2]),],
    )

    robot_controllers = PathJoinSubstitution([FindPackageShare("anymal_d_simple_description"), "config", "pos_controller.yaml",])

    #Controller manager load the controllers defined in the yaml file
    control_node = Node(
        package="controller_manager", #In order to communicate with the hardware, this controller requires a modification in the urdf
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
    )#--controller-manager /controller-manager is used to specify that the node controller manager is named /controller-manager
        #--controller-manager va a specificare quale nodo è il controller_manager. Se il controller_manager si chiama con l'underscore
    #controller_manager, ma tu dici ai ros2_controllers che si chiama con il trattino (/controller-manager), allora i ros2_controllers non lo trovano


    delay_joint_traj_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=gz_spawn_entity,
            on_exit=[joint_trajectory_controller],
        )
    )

    delay_joint_state_broadcaster = (
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=joint_trajectory_controller,
                on_exit=[joint_state_broadcaster],
            )
        )
    )
 



    nodes_to_start = [
        joint_state_publisher_node,
        robot_state_publisher_node, #publish pose of each link and transformation to know ehre the robot is
        #rviz_node,
        gazebo_ignition,
        gz_spawn_entity,
        #control_node, #if your hardware interface is the simulator, the ros-control will be the one specified in the plugin gazebo, 
        #joint_trajectory_controller,
        #joint_state_broadcaster, #publish the state of the robot as sensor-masgs for control (like the joints pos e vel)
        delay_joint_traj_controller, #ros controller chosen. I could also use a psition controller
        delay_joint_state_broadcaster,
    ]
    
    """In rviz, quando selezioni il modello, devi mettere il topic /robot_descriptio in Description topic"""

    return LaunchDescription(declared_arguments + nodes_to_start) #its argument must to be a list