import numpy as np
import PySimpleGUI as sg
import cv2
import os.path
import os
import dlib
import json
import time

#This bit is present in both sets of code, and is used to make sure that file references direct to the right place
root = os.path.normpath(os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists(root+r'\temp'):
    os.makedirs(root+r'\temp')

#The dlib correlation tracker is used to follow the face once it has been discovered by the cv2 haarcascade classifier
#This face detection method is pretty much out the box, I haven't done anything unique here
tracker = dlib.correlation_tracker()
faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def correct_image(impath):
    #This function is used to distort our render of what the screen looks like from an angle and reproject it onto a screen which is not perspective distorted
    #If you'd like a visual example of what this means, you can run the function 
    if os.access(impath, os.W_OK):
        img = cv2.imread(impath) #Open the image
        imgscale = img.shape #Find image dimensions
        with open(r'C:\Users\robda\Documents\LookingGlass\temp\corndat.json', 'r') as openfile:
            json_object = json.load(openfile) #This loads the corner coords produced by get_corner_coords in the Blender script
            fcoords = np.zeros([4,2])
        for i in range(4):
            fcoords[i] = json_object[str(i)]
            fcoords[i][1] = imgscale[0]-fcoords[i][1] #Difference in convention - blender coords have y = 0 at the bottom, matlab.pyplot has y = 0 at top
        w = imgscale[1]
        h = imgscale[0]
        idcoords = np.array([[0,0], [0, h], [w, 0], [w,h]]) #The coordinates of the undistorted screen - just the corners of the image
        idcoords = np.float32(idcoords) #functions to obtain M, cimg require 64-bit float coordinates
        fcoords = np.float32(fcoords)
        M = cv2.getPerspectiveTransform(fcoords, idcoords) #Find the transforming matrix from the warped and the unwarped coordinates
        cimg = cv2.warpPerspective(img, M, (w, h)) #Warp the image by the transforming matrix
        os.replace(impath, root+r'/temp/bu.jpg') #bu is a backup image used if there is an error finding the actual image
        return cimg
    else:
        img = cv2.imread(root+r'/temp/bu.jpg') #here we read bu because there was an error finding the actual image given by impath
        return img

def render_offaxis():
    #Main program which does everything
    impath = root + r'/temp/perimg.jpg' #Path to the perspective image
    sq_layout = [[sg.Image(filename ='', key = '-IMAGE-', expand_x = True, expand_y = True)]] #This defines the canvas elements used to construct the PySimpleGUI
    window = sg.Window("BlendViewer", sq_layout, finalize=True, element_justification = 'center', location = (0, 0), size = (960, 540)) #Create the GUI
    pos = {'pos':(15, 0, -0)} #Initial camera position
    json_object = json.dumps(pos, indent = 4)
    with open('posfile.json', 'w') as outfile:
        outfile.write(json_object) #Write the .json file which set_cam_pos in Blender program uses
    img = correct_image(impath) #Correct the first perspective image we've found
    imgbytes = cv2.imencode(".png", img)[1].tobytes() #Convert image to bytes
    window["-IMAGE-"].update(data=imgbytes) #Display the image
    cap = cv2.VideoCapture(0) #This is the webcam view
    trackingface = 0 #Used to check if a face is currently being followed by the dlib tracker
    try:
        while True:
            event,values = window.read(timeout = 1) #Checking if we've done anything in the GUI - in this case just checking if we close the window
            if event == "Exit" or event == sg.WIN_CLOSED:
                break
            ret, frame = cap.read() #Current webcam frame
            fshape = frame.shape #Dimensions of the frame
            if not trackingface:
                gframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) #Convert frame to grayscale
                faces = faceCascade.detectMultiScale(gframe, 1.3, 5) #Detect face in frame
                #Next section just finds the position and size of the faces
                maxArea = 0
                x = 0
                y = 0
                w = 0
                h = 0
                for(_x,_y,_w,_h) in faces:
                    if _w*_h > maxArea:
                        x = int(_x)
                        y = int(_y)
                        w = int(_w)
                        h = int(_h)
                        maxArea = w*h
                if maxArea > 0: #If there is a face
                    #Start dlib tracking
                    tracker.start_track(frame, dlib.rectangle(x-10, y-20, x+w+10, y+h+20))
                    t_x = tracker.get_position().left() #Horizontal position of tracked face
                    t_y = tracker.get_position().top() #Vertical position of tracked face
                    trackingface = 1 #Confirm we are tracking a face
            else:
                trackingquality = tracker.update(frame) #Quality of dlib tracker
                if trackingquality >= 8.75: #This is our condition for a tracking being good
                    #Since we are still tracking, we update the tracked position
                    tracked_position = tracker.get_position()
                    t_x = tracked_position.left()
                    t_y = tracked_position.top()
                else:
                    trackingface = 0 #The quality of our track wasn't good enough, so we need to find a new face on the next loop
                if not os.path.exists(root+r'/posfile.json'): #We only create a new posfile if the blender version has deleted the last one
                    t1 = time.time() #Only used if you decide to display framerate in line 109
                    #Next section creates the posfile we use to update camera position
                    pos = {'pos':(15, (-(t_x-fshape[1]/2)/fshape[1])*(4.592), (-(t_y-fshape[0]/2)/fshape[1])*(2.607))}
                    json_object = json.dumps(pos, indent = 4)
                    with open('posfile.json', 'w') as outfile:
                        outfile.write(json_object)
                    #Now we can just correct the next image which has been captured
                    img = correct_image(impath)
                    imgbytes = cv2.imencode(".png", img)[1].tobytes()
                    window["-IMAGE-"].update(data=imgbytes)
                    #Uncomment next line if you want to see the framerate
                    #print(1/(time.time()-t1))
        #Close GUI if we click close
        window.close()
    except KeyboardInterrupt:
        print('Stopping')
        window.close()
        pass
        
render_offaxis()
    




