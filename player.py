from pandac.PandaModules import *
import math

class Player( object ):

    KeyMap = { "w":0, "a":0, "s":0, "d":0, "space":0 }

    Accel = 60
    AirDeaccel     = 150
    PassiveDeaccel = 200
    ActiveDeaccel  = 400

    CurSpeed = 0
    MaxSpeed = 80
    CurStrafeSpeed = 0
    MaxStrafeSpeed = 40

    Falling           = False
    Jumping           = False
    DoubleJumping     = False
    ReadyToDoubleJump = False

    CurJumpMomentum = 0
    MaxJumpMomentum = 3 # Higher value results in higher jumps
    JumpMultiplier  = 7 # Higher value will cause player to rise and fall faster

    MouseSensitivity = 0.2 # Higher value means faster camera movement
    CameraFOV      = 80
    CameraCurShake = 0
    CameraMaxShake = 0.025 # Higher value results in wider shaker
    CameraShakeDt  = 0.18  # Higher value results in faster shaker
    PitchMax       = 60    # Camera can't look up or down past this value

    def __init__( self ):
        """ inits the player """
        self.loadModel()
        self.setUpCamera()
        self.createCollisions()
        self.attachControls()
        taskMgr.add( self.mouseUpdate, 'MouseTask' )
        taskMgr.add( self.moveUpdate,  'MoveTask'  )
        taskMgr.add( self.jumpUpdate,  'JumpTask'  )


    def loadModel( self ):
        """ make the nodepath for player """
        self.player = NodePath( 'player' )
        self.player.reparentTo( render )
        self.player.setPos( 0, 0, 2 )
        self.player.setScale( .05 )


    def setUpCamera( self ):
        """ puts camera at the players node """
        pl =  base.cam.node().getLens()
        pl.setFov( self.CameraFOV )
        base.cam.node().setLens( pl )
        base.camera.reparentTo( self.player )


    def createCollisions( self ):
        """ create a collision solid and rays for the player """
        self.playerCol = CollisionNode( 'player' )
        self.playerCol.addSolid( CollisionSphere( 0, 0, 0, 3 ) )
        self.playerColNp = self.player.attachNewNode( self.playerCol )
        base.cTrav.addCollider( self.playerColNp, base.pusher )
        base.pusher.addCollider( self.playerColNp, self.player, base.drive.node() )

        # init player's floor collisions
        self.groundRay = CollisionRay()
        self.groundRay.setOrigin( 0, 0, -.2 )
        self.groundRay.setDirection( 0, 0, -1 )

        self.groundCol = CollisionNode( 'playerGroundRay' )
        self.groundCol.addSolid( self.groundRay )
        self.groundCol.setFromCollideMask( BitMask32.bit(0) )
        self.groundCol.setIntoCollideMask( BitMask32.allOff() )

        self.groundColNp = self.player.attachNewNode( self.groundCol )
        self.groundHandler = CollisionHandlerQueue()
        base.cTrav.addCollider( self.groundColNp, self.groundHandler )

        # init player's forward collisions
        self.forwardRay = CollisionRay()
        self.forwardRay.setOrigin( 0, 0, -.2 )
        self.forwardRay.setDirection( 0, 1, 0 )

        self.forwardCol = CollisionNode( 'playerForwardRay' )
        self.forwardCol.addSolid( self.forwardRay )
        self.forwardCol.setFromCollideMask( BitMask32.bit(0) )
        self.forwardCol.setIntoCollideMask( BitMask32.allOff() )

        self.forwardColNp = self.player.attachNewNode( self.forwardCol )
        self.forwardHandler = CollisionHandlerQueue()
        base.cTrav.addCollider( self.forwardColNp, self.forwardHandler )

        # Uncomment this line to see the collision rays
        #self.groundColNp.show()
        #self.forwardColNp.show()

        # Uncomment this line to show a visual representation of the 
        # collisions occuring
        #base.cTrav.showCollisions(render)
       

    def attachControls( self ):
        """ attach key events """
        base.accept( "space",    self.setKey, [ "space", 1  ] )
        base.accept( "space-up", self.setKey, [ "space", 0  ] )
        base.accept( "w",    self.setKey, [ "w", 1  ] )
        base.accept( "w-up", self.setKey, [ "w", 0  ] )
        base.accept( "s",    self.setKey, [ "s", 1  ] )
        base.accept( "s-up", self.setKey, [ "s", 0  ] )
        base.accept( "a",    self.setKey, [ "a", 1  ] )
        base.accept( "a-up", self.setKey, [ "a", 0  ] )
        base.accept( "d",    self.setKey, [ "d", 1  ] )
        base.accept( "d-up", self.setKey, [ "d", 0  ] )


    def setKey( self, key, value ):

        if key == "space" and value == 0 and self.Jumping == True and self.DoubleJumping == False:
            self.ReadyToDoubleJump = True

        self.KeyMap[ key ] = value


    def mouseUpdate( self, task ):

        md = base.win.getPointer(0)
        x = md.getX()
        y = md.getY()

        if base.win.movePointer( 0, base.win.getXSize()/2, base.win.getYSize()/2 ):

            self.player.setH( self.player.getH() - ( x - base.win.getXSize() / 2 ) * self.MouseSensitivity )

            pitch = base.camera.getP() - ( y - base.win.getYSize() / 2 ) * self.MouseSensitivity
            if pitch < -self.PitchMax: pitch = -self.PitchMax
            elif pitch > self.PitchMax: pitch = self.PitchMax
            base.camera.setP( pitch )

        return task.cont


    def moveUpdate( self, task ):

        # Get the closest obstacle from the forward ray
        px = self.player.getX()
        py = self.player.getY()

        lowestDist = 1000

        for i in range( self.forwardHandler.getNumEntries() ):

            entry = self.forwardHandler.getEntry( i )
            if entry.getIntoNode().getName() == "Cube":

                point = entry.getSurfacePoint( render )
                x = point.getX()
                y = point.getY()
                dist = math.sqrt( (px-x)*(px-x) + (py-y)*(py-y) )

                if dist < lowestDist:
                    lowestDist = dist

        #print lowestDist

        # Only let player alter his course if not jumping (he can still alter it by moving the camera, though)
        if self.Falling == False and self.Jumping == False:

            # Accelerate forward
            if self.KeyMap["w"] == 1:

                # Can't accelerate into a brick wall
                if lowestDist > 0.24:

                    if self.CurSpeed < 0:
                        self.CurSpeed += self.ActiveDeaccel * globalClock.getDt()
                    else:
                        self.CurSpeed += self.Accel * globalClock.getDt()

                    if self.CurSpeed > self.MaxSpeed:
                        self.CurSpeed = self.MaxSpeed

                else:
                    self.CurSpeed = 0

            # Accelerate backward
            elif self.KeyMap["s"] == 1:

                if self.CurSpeed > 0:
                    self.CurSpeed -= self.ActiveDeaccel * globalClock.getDt()
                else:
                    self.CurSpeed -= self.Accel * globalClock.getDt()

                if self.CurSpeed < -self.MaxSpeed/2:
                    self.CurSpeed = -self.MaxSpeed/2

            # If not going forward or backward, slow down until speed is 0
            else:

                if self.CurSpeed > 0:
                    self.CurSpeed -= self.PassiveDeaccel * globalClock.getDt()
                    if self.CurSpeed < 0:
                        self.CurSpeed = 0

                elif self.CurSpeed < 0:
                    self.CurSpeed += self.PassiveDeaccel * globalClock.getDt()
                    if self.CurSpeed > 0:
                        self.CurSpeed = 0

            # Accelerate right
            if self.KeyMap["d"] == 1:

                if self.CurStrafeSpeed < 0:
                    self.CurStrafeSpeed += self.ActiveDeaccel * globalClock.getDt()
                else:
                    self.CurStrafeSpeed += self.Accel * globalClock.getDt()

                if self.CurStrafeSpeed > self.MaxStrafeSpeed:
                    self.CurStrafeSpeed = self.MaxStrafeSpeed

            # Accelerate left
            elif self.KeyMap["a"] == 1:

                if self.CurStrafeSpeed > 0:
                    self.CurStrafeSpeed -= self.ActiveDeaccel * globalClock.getDt()
                else:
                    self.CurStrafeSpeed -= self.Accel * globalClock.getDt()

                if self.CurStrafeSpeed < -self.MaxStrafeSpeed:
                    self.CurStrafeSpeed = -self.MaxStrafeSpeed

            # If not going right or left, slow down until speed is 0
            else:

                if self.CurStrafeSpeed > 0:
                    self.CurStrafeSpeed -= self.PassiveDeaccel * globalClock.getDt()
                    if self.CurStrafeSpeed < 0:
                        self.CurStrafeSpeed = 0

                elif self.CurStrafeSpeed < 0:
                    self.CurStrafeSpeed += self.PassiveDeaccel * globalClock.getDt()
                    if self.CurStrafeSpeed > 0:
                        self.CurStrafeSpeed = 0

        # Update player position
        self.player.setY( self.player, self.CurSpeed * globalClock.getDt() )
        self.player.setX( self.player, self.CurStrafeSpeed * globalClock.getDt() )

        # Shake camera when player is running
        # Don't shake camera when player has stopped or is in mid-air
        if self.CurSpeed != 0:

            # The camera will shake most when MaxSpeed is reached
            relSpeed = self.CurSpeed / self.MaxSpeed
            if self.CurSpeed < 0: relSpeed *= -1

            base.camera.setX( base.camera.getX() + self.CameraCurShake )
            base.camera.setR( base.camera.getR() + self.CameraCurShake )
            self.CameraCurShake += relSpeed * self.CameraShakeDt * globalClock.getDt()

            if self.CameraCurShake > self.CameraMaxShake * relSpeed:
                self.CameraCurShake = self.CameraMaxShake * relSpeed
                self.CameraShakeDt *= -1
            elif self.CameraCurShake < -self.CameraMaxShake * relSpeed:
                self.CameraCurShake = -self.CameraMaxShake * relSpeed
                self.CameraShakeDt *= -1

        else:
            self.CameraCurShake = 0
            base.camera.setX(0)
            base.camera.setR(0)

        if self.Falling == True or self.Jumping == True:
            self.CameraCurShake = 0
            base.camera.setX(0)
            base.camera.setR(0)

        return task.cont


    def jumpUpdate( self, task ):

        # Get the highest Z from the down casting ray
        highestZ = -1000
        for i in range( self.groundHandler.getNumEntries() ):
            entry = self.groundHandler.getEntry(i)
            z = entry.getSurfacePoint(render).getZ()
            if z > highestZ and entry.getIntoNode().getName() == "Cube":
                highestZ = z

        # Gravity effects and jumps
        self.player.setZ( self.player.getZ() + self.CurJumpMomentum * globalClock.getDt() )
        self.CurJumpMomentum -= self.JumpMultiplier * globalClock.getDt()

        zdif = self.player.getZ() - highestZ

        # Detecting a fall
        if zdif >= 0.35 and self.Jumping == False:

            self.Falling = True

        # Detecting the end of a fall/jump, or preventing a really small one
        elif zdif < 0.3 or ( zdif < 0.35 and self.Jumping == False ):

            self.player.setZ( highestZ + 0.3 )
            self.CurJumpMomentum = 0
            self.Falling = False
            self.Jumping = False
            self.DoubleJumping = False
            self.ReadyToDoubleJump = False

        # Player wants to jump
        if self.KeyMap["space"] == 1 and self.Falling == False:

            if self.Jumping == False:

                self.CurJumpMomentum = self.MaxJumpMomentum
                self.Jumping = True

                # Jumping in a certain direction can give you horizontal momentum, at the price of vertical momentum
                if self.KeyMap["w"] == 0:
                    if self.KeyMap["s"] == 1:

                        self.CurJumpMomentum *= 0.8
                        self.CurStrafeSpeed *= 0.1
                        if self.CurSpeed > 0:
                            self.CurSpeed = - self.MaxSpeed / 2 + self.CurSpeed * 0.25
                        else:
                            self.CurSpeed = - self.MaxSpeed / 2

                    elif self.KeyMap["d"] == 1:

                        self.CurJumpMomentum *= 0.8
                        self.CurSpeed *= 0.1
                        self.CurStrafeSpeed = self.MaxStrafeSpeed * 1.5

                    elif self.KeyMap["a"] == 1:

                        self.CurJumpMomentum *= 0.8
                        self.CurSpeed *= 0.1
                        self.CurStrafeSpeed = -self.MaxStrafeSpeed * 1.5

            elif self.ReadyToDoubleJump == True:

                self.CurJumpMomentum = self.MaxJumpMomentum
                self.DoubleJumping = True
                self.ReadyToDoubleJump = False

        return task.cont