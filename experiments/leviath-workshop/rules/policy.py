"""Owned-world rule model. Caller roles are declarations, not authenticated identities."""
import copy,hashlib,json,re
VERSION='0.2.0'
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def initial():
 return {'version':VERSION,'world':'MORROWIND_FIRST','owner':'LOCAL_PLAYER','runtime':'OPENMW_EXISTING_WORLD','ingress':'CLOSED','centerVisibility':'PRIVATE','guests':{},'mailboxes':{'COLISEUM':[]},'challenges':{},'receipts':[],'networkEffects':0,'gameDay':0,'ownerPosition':[0,0],'secretDepot':{},'ownerInventory':[]}
def identifier(s):
 if not isinstance(s,str) or not re.fullmatch('[A-Z][A-Z0-9_]{0,31}',s):raise ValueError('Invalid ID')
 return s
def owner(role):
 if role!='OWNER_DECLARED':raise ValueError('Owner decision required')
def transition(state,action,data,role):
 s=copy.deepcopy(state)
 if action=='receiver':
  owner(role)
  if data.get('mode') not in ('CLOSED','PUBLIC_COLISEUM'):raise ValueError('Unknown receiver mode')
  s['ingress']=data['mode']
  if data['mode']=='CLOSED':s['guests']={}
 elif action=='arrive':
  if s['ingress']!='PUBLIC_COLISEUM':raise ValueError('Receiver closed')
  guest=identifier(data['guest'])
  if guest in s['guests']:raise ValueError('Guest already admitted')
  if data.get('zone','COLISEUM')!='COLISEUM':raise ValueError('Guests enter only COLISEUM')
  s['guests'][guest]={'zone':'COLISEUM','inventoryMode':'ARENA_LOCAL','progressionEffects':'GUEST_ONLY'}
 elif action=='move_guest':
  guest=identifier(data['guest'])
  if guest not in s['guests'] or data['zone']!='COLISEUM':raise ValueError('Outside admitted guest zone')
 elif action=='mail':
  guest=identifier(data['guest']);text=data['text']
  if guest not in s['guests']:raise ValueError('Guest not admitted')
  if not isinstance(text,str) or not 1<=len(text)<=2000 or any(ord(c)<32 and c not in '\n\t' for c in text):raise ValueError('Invalid plain text message')
  if len(s['mailboxes']['COLISEUM'])>=100:raise ValueError('Mailbox capacity reached')
  s['mailboxes']['COLISEUM'].append({'senderDeclared':guest,'text':text,'type':'PLAIN_TEXT_ONLY','recipient':'WORLD_OWNER','location':'COLISEUM'})
 elif action=='leave_gift':
  guest=identifier(data['guest']);gid=identifier(data['id'])
  if guest not in s['guests']:raise ValueError('Guest not admitted')
  if gid in s['secretDepot']:raise ValueError('Duplicate delivery')
  items=data.get('items',[]);message=data.get('message','')
  if not isinstance(items,list) or len(items)>20:raise ValueError('Invalid gift items')
  if not isinstance(message,str) or len(message)>2000 or any(ord(c)<32 and c not in '\n\t' for c in message):raise ValueError('Invalid message')
  if not items and not message:raise ValueError('Empty delivery')
  for item in items:
   # Bound item references and quantities; engine item definitions are a separate adapter.
   if not isinstance(item,dict) or set(item)!={'itemId','quantity'}:raise ValueError('Item reference and quantity required')
   identifier(item['itemId'])
   if type(item['quantity']) is not int or not 1<=item['quantity']<=1000000:raise ValueError('Invalid quantity')
  s['secretDepot'][gid]={'senderDeclared':guest,'items':copy.deepcopy(items),'message':message,'impactDay':s['gameDay'],'state':'SECRET_DEPOT','courierPosition':[0,0],'deliveredDay':None}
 elif action=='owner_position':
  owner(role);position=data.get('position')
  if not isinstance(position,list) or len(position)!=2 or any(type(v) is not int or abs(v)>10000 for v in position):raise ValueError('Invalid map cell coordinates')
  s['ownerPosition']=position[:]
 elif action=='advance_days':
  owner(role);days=data.get('days')
  if type(days) is not int or not 1<=days<=365:raise ValueError('Invalid game-day advance')
  for _ in range(days):
   s['gameDay']+=1
   for parcel in s['secretDepot'].values():
    if parcel['state'] not in ('SECRET_DEPOT','COURIER_TRAVEL'):continue
    if s['gameDay']-parcel['impactDay']<2:continue
    parcel['state']='COURIER_TRAVEL'
    # Prototype tuning: two game days from impact before departure, ten grid cells/day.
    budget=10;pos=parcel['courierPosition'];target=s['ownerPosition']
    for axis in (0,1):
     delta=target[axis]-pos[axis];step=min(abs(delta),budget)
     pos[axis]+=step if delta>0 else -step;budget-=step
    if pos==target:
     parcel['state']='COURIER_ARRIVED';parcel['deliveredDay']=s['gameDay']
 elif action=='claim_gift':
  owner(role);gid=identifier(data['id'])
  if gid not in s['secretDepot'] or s['secretDepot'][gid]['state']!='COURIER_ARRIVED':raise ValueError('Courier has not arrived or gift already claimed')
  parcel=s['secretDepot'][gid]
  s['ownerInventory'].extend(copy.deepcopy(parcel['items']));parcel['state']='CLAIMED'
 elif action=='propose_challenge':
  cid=identifier(data['id']);scope=data['scope'];channel=data['channel']
  if scope!='OWNED_CHALLENGE_WORLD':raise ValueError('Challenge scope not bound to own world')
  if channel!='EXTERNAL_ENGINEERING':raise ValueError('In-game console cheating is excluded')
  if data.get('sourceOpen') is not True or not re.fullmatch('[0-9a-f]{64}',data.get('sourceDigest','')):raise ValueError('Open source and bound source digest required')
  if cid in s['challenges']:raise ValueError('Duplicate challenge')
  s['challenges'][cid]={'scope':scope,'channel':channel,'sourceDigest':data['sourceDigest'],'state':'PENDING_REVIEW','reward':'UNASSIGNED','evidenceCeiling':'DECLARED_PROPOSAL'}
 elif action=='accept_challenge':
  owner(role);cid=identifier(data['id']);proposal=s['challenges'][cid]
  required={'SOURCE_LICENSE','REPRODUCIBLE_BUILD','GAME_RULES','RESOURCE_BUDGET','LOCAL_RUNTIME','REWARD_SCOPE'}
  checks=data.get('checks',{})
  if set(checks)!=required or any(v is not True for v in checks.values()):raise ValueError('Bound review checks incomplete')
  if data.get('reviewedSourceDigest')!=proposal['sourceDigest']:raise ValueError('Review refers to different source')
  # This is a decision model, not a verifier that ran those checks.
  proposal.update({'state':'OWNER_ACCEPTED_DECLARED','reward':'OWNED_WORLD_CHAMPION_BADGE','evidenceCeiling':'DECLARED_REVIEW_NOT_ENGINE_AUDIT'})
 else:raise ValueError('Unknown action')
 s['receipts'].append({'sequence':len(s['receipts'])+1,'action':action,'inputStateDigest':digest(state),'outputCoreDigest':digest({k:v for k,v in s.items() if k!='receipts'}),'actorRole':'DECLARED_ONLY'})
 return s
