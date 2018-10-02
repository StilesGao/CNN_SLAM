# Libraries
import numpy as np 
import cv2
import tensorflow as tf
import sys
import time
import argparse

# Modules
import pose_estimation.refine_depth_map as refine_depth_map
import pose_estimation.depth_map_fusion as depth_map_fusion
import pose_estimation.camera_pose_estimation as camera_pose_estimation
import pose_estimation.define_depth_map as define_depth_map
import pose_estimation.find_uncertainty as find_uncertainty
from pose_estimation import monodepth

im_size = (480,640)
sigma_p = 0 # Some white noise variance thing
index_matrix = np.dstack(np.meshgrid(np.arange(480),np.arange(640),indexing = 'ij'))

parser = argparse.ArgumentParser(description='Monodepth TensorFlow implementation.')

parser.add_argument('--mono_checkpoint_path',  type=str,   help='path to a specific checkpoint to load',required=True)
parser.add_argument('--input_height',     type=int,   help='input height', default=480)
parser.add_argument('--input_width',      type=int,   help='input width', default=640)

args = parser.parse_args()

# Video cam
cam = cv2.VideoCapture(0)

def get_camera_image():
	'''
	Returns:

	* ret: Whether camera captured or not 
	* frame: 3 channel image
	* frame_grey greyscale
	'''
	ret,frame = cam.read()
	frame_grey = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY) # Using single channel image
	return ret,frame,frame_grey

def get_camera_matrix(path=None): 
	'''
	Read intrinsic matrix from npy file.

	Change to read from camera calib file.

	Use identity matrix for testing.
	'''
	if path:
		return np.load(path)
	else:
		return np.eye(3)

def _exit_program():


def main():

	# INIT monodepth session
	sess=monodepth.init_monodepth(args.mono_checkpoint_path)

	# INIT camera matrix
	cam_matrix = get_camera_matrix()

	try: 
		cam_matrix_inv = np.linalg.inv(cam_matrix)
	except:
		raise (Error, "Verify camera matrix")

	# Image is 3 channel, frame is grayscale
	ret,image,frame = get_camera_image()

	# List of keyframe objects
	K = []

	# Append first frame to K
	ini_depth = monodepth.get_cnn_depth(sess,image)

    # Initalisation
	ini_uncertainty = find_uncertainty.get_initial_uncertainty()
	ini_pose = camera_pose_estimation.get_initial_pose()

	K.append(Keyframe(ini_pose,ini_depth,ini_uncertainty,frame)) 
	cur_keyframe = K[0]
	cur_index = 0
	prev_frame = cur_keyframe.I
	prev_pose = cur_keyframe.T
	while(True):

		ret,image,frame = get_camera_image() # frame is the numpy array

		if not ret:
			_exit_program()

        # Finds the high gradient pixel locations in the current frame
		u = camera_pose_estimation.get_highgrad_element(frame) 

        # Finds pose of current frame by minimizing photometric residual (wrt prev keyframe)
		T = camera_pose_estimation.minimize_cost_func(u,frame,cur_keyframe) 
            
		if check_keyframe(T):			
			# If it is a keyframe, add it to K after finding depth and uncertainty map                    
			depth = monodepth.get_cnn_depth(sess,image)	
			cur_index += 1
			uncertainty = find_uncertainty.get_uncertainty(T,D,K[cur_index - 1])
			T_abs = np.matmul(T,cur_keyframe.T) # absolute pose of the new keyframe
			K.append(Keyframe(T_abs,depth,uncertainty,frame))
			K[cur_index].D,K[cur_index].U = depth_map_fusion.fuse_depth_map(K[cur_index],K[cur_index - 1])
			cur_keyframe = K[cur_index]

			update_pose_graph()
			do_graph_optimization()

		else: # Refine and fuse depth map. Stereo matching consecutive frame
			D_frame = stereo_match.stereo_match(prev_frame,frame,prev_pose,T)
			U_frame = find_uncertainty.get_uncertainty(T,D,cur_keyframe)
			frame_obj = Keyframe(T,D_frame,U_frame,frame) # frame as a keyframe object
			cur_keyframe.D,cur_keyframe.U = depth_map_fusion.fuse_depth_map(frame_obj,cur_keyframe)
		
		_delay()
		prev_frame = frame
		prev_pose = T
		continue

if __name__ == "__main__":
	main()