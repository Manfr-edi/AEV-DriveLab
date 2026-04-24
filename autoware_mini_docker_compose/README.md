## Prerequisite
  1. Download [Carla 0.9.13](https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/CARLA_0.9.13.tar.gz) and extract PythonAPI folder and place it `autoware_mini/CARLA_ROOT/`

## To build autoware image 
   
     docker compose build autoware_mini

## To start autoware container

    docker compose up -d autoware_mini

## Get into autoware_mini container 

    docker exec -it autoware_mini bash 
    catkin build 
    .  devel/setup.bash 
    roslaunch autoware_mini start_carla.launch
