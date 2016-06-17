import tensorflow as tf
import tf_lib as tfl
import util
import ssbm

floatType = tf.float32

class FloatEmbedding:
  def __init__(self, scale=None, bias=None):
    self.scale = scale
    self.bias = bias
    self.size = 1
  
  def __call__(self, t):
    if t.dtype is not floatType:
      t = tf.cast(t, floatType)
    
    if self.bias:
      t += self.bias
    
    if self.scale:
      t *= self.scale
    
    return tf.expand_dims(t, -1)

embedFloat = FloatEmbedding()

class OneHotEmbedding:
  def __init__(self, size):
    self.size = size
  
  def __call__(self, t):
    t = tf.cast(t, tf.int64)
    return tf.one_hot(t, self.size, 1.0, 0.0)

class StructEmbedding:
  def __init__(self, embedding):
    self.embedding = embedding
    
    self.size = 0
    for _, op in embedding:
      self.size += op.size
  
  def __call__(self, struct):
    embed = []
    rank = None
    for field, op in self.embedding:
      with tf.name_scope(field):
        t = op(struct[field])
        if rank is None:
          rank = tf.shape(tf.shape(t))[0]
        
        embed.append(t)
    return tf.concat(rank-1, embed)

class ArrayEmbedding:
  def __init__(self, op, permutation):
    self.op = op
    self.permutation = permutation
    self.size = len(permutation) * op.size
  
  def __call__(self, array):
    embed = []
    rank = None
    for i in self.permutation:
      with tf.name_scope(str(i)):
        t = self.op(array[i])
        r = len(t.get_shape())
        if rank is None:
          rank = r
        else:
          assert(r == rank)
      
        embed.append(t)
    return tf.concat(rank-1, embed)

stickEmbedding = [
  ('x', embedFloat),
  ('y', embedFloat)
]

embedStick = StructEmbedding(stickEmbedding)

# TODO: embed entire controller
controllerEmbedding = [
  ('button_A', embedFloat),
  ('button_B', embedFloat),
  ('button_X', embedFloat),
  ('button_Y', embedFloat),
  ('button_L', embedFloat),
  ('button_R', embedFloat),

  #('trigger_L', embedFloat),
  #('trigger_R', embedFloat),

  ('stick_MAIN', embedStick),
  ('stick_C', embedStick),
]

embedController = StructEmbedding(controllerEmbedding)

maxAction = 0x017E
numActions = 1 + maxAction

class ActionEmbedding:
  def __init__(self, action_space=32, **kwargs):
    self.one_hot = OneHotEmbedding(numActions)
    self.helper = tfl.FCLayer(numActions, action_space)
    self.size = action_space
  
  def __call__(self, x):
    return self.helper(self.one_hot(x))

maxCharacter = 32 # should be large enough?
maxJumps = 8 # unused

class PlayerEmbedding(StructEmbedding):
  def __init__(self, **kwargs):
    embedAction = ActionEmbedding(**kwargs)

    playerEmbedding = [
      ("percent", FloatEmbedding(scale=0.01)),
      ("facing", embedFloat),
      ("x", FloatEmbedding(scale=0.1)),
      ("y", FloatEmbedding(scale=0.1)),
      ("action_state", embedAction),
      # ("action_counter", embedFloat),
      ("action_frame", FloatEmbedding(scale=0.02)),
      # ("character", one_hot(maxCharacter)),
      ("invulnerable", embedFloat),
      ("hitlag_frames_left", embedFloat),
      ("hitstun_frames_left", embedFloat),
      ("jumps_used", embedFloat),
      ("charging_smash", embedFloat),
      ("shield_size", embedFloat),
      ("in_air", embedFloat),
      ('speed_air_x_self', embedFloat),
      ('speed_ground_x_self', embedFloat),
      ('speed_y_self', embedFloat),
      ('speed_x_attack', embedFloat),
      ('speed_y_attack', embedFloat),

      #('controller', embedController)
    ]
    
    super(PlayerEmbedding, self).__init__(playerEmbedding)

"""
maxStage = 64 # overestimate
stageSpace = 32

with tf.variable_scope("embed_stage"):
  stageHelper = tfl.makeAffineLayer(maxStage, stageSpace)

def embedStage(stage):
  return stageHelper(one_hot(maxStage)(stage))
"""

class GameEmbedding(StructEmbedding):
  def __init__(self, swap=False, **kwargs):
    embedPlayer = PlayerEmbedding(**kwargs)
    
    players = [0, 1]
    if swap: players.reverse()
    
    gameEmbedding = [
      ('players', ArrayEmbedding(embedPlayer, players)),

      #('frame', c_uint),
      # ('stage', embedStage)
    ]
    
    super(GameEmbedding, self).__init__(gameEmbedding)

def embedEnum(enum):
  return OneHotEmbedding(len(enum))

simpleControllerEmbedding = [
  ('button', embedEnum(ssbm.SimpleButton)),
  ('stick_MAIN', embedEnum(ssbm.SimpleStick)),
]

embedSimpleController = StructEmbedding(simpleControllerEmbedding)
#embedded_controls = embedController(train_controls)

action_size = len(ssbm.simpleControllerStates)
embedAction = OneHotEmbedding(action_size)

