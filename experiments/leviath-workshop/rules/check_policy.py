from pathlib import Path
import json,unittest,hashlib
from policy import initial,transition,digest,VERSION
class PolicyChecks(unittest.TestCase):
 def denied(self,s,action,data,role='GUEST_DECLARED'):
  before=digest(s)
  with self.assertRaises(ValueError):transition(s,action,data,role)
  self.assertEqual(digest(s),before)
 def opened(self):return transition(initial(),'receiver',{'mode':'PUBLIC_COLISEUM'},'OWNER_DECLARED')
 def test_closed_by_default(self):self.denied(initial(),'arrive',{'guest':'TRAVELER'})
 def test_owner_controls_receiver(self):self.denied(initial(),'receiver',{'mode':'PUBLIC_COLISEUM'})
 def test_arrival_only_arena(self):
  s=self.opened();self.denied(s,'arrive',{'guest':'TRAVELER','zone':'HOME'})
  s=transition(s,'arrive',{'guest':'TRAVELER'},'GUEST_DECLARED');self.assertEqual(s['guests']['TRAVELER']['zone'],'COLISEUM')
  self.denied(s,'move_guest',{'guest':'TRAVELER','zone':'HOME'})
 def test_closing_removes_local_guest_sessions(self):
  s=transition(self.opened(),'arrive',{'guest':'TRAVELER'},'GUEST_DECLARED')
  s=transition(s,'receiver',{'mode':'CLOSED'},'OWNER_DECLARED');self.assertEqual(s['guests'],{})
 def test_mail_plain_text_and_limits(self):
  s=transition(self.opened(),'arrive',{'guest':'TRAVELER'},'GUEST_DECLARED')
  s=transition(s,'mail',{'guest':'TRAVELER','text':'Hello from GREEN'},'GUEST_DECLARED');self.assertEqual(len(s['mailboxes']['COLISEUM']),1)
  self.denied(s,'mail',{'guest':'OTHER','text':'unknown sender'})
  self.denied(s,'mail',{'guest':'TRAVELER','text':'x'*2001})
 def test_console_and_foreign_game_excluded(self):
  d={'id':'BOOST','scope':'OWNED_CHALLENGE_WORLD','channel':'GAME_CONSOLE','sourceOpen':True,'sourceDigest':'a'*64}
  self.denied(initial(),'propose_challenge',d)
  d.update(channel='EXTERNAL_ENGINEERING',scope='THIRD_PARTY_GAME');self.denied(initial(),'propose_challenge',d)
 def test_challenge_review_binds_source_and_owner(self):
  d={'id':'BOOST','scope':'OWNED_CHALLENGE_WORLD','channel':'EXTERNAL_ENGINEERING','sourceOpen':True,'sourceDigest':'a'*64}
  s=transition(initial(),'propose_challenge',d,'GUEST_DECLARED')
  self.assertEqual(s['challenges']['BOOST']['state'],'PENDING_REVIEW')
  checks={k:True for k in ['SOURCE_LICENSE','REPRODUCIBLE_BUILD','GAME_RULES','RESOURCE_BUDGET','LOCAL_RUNTIME','REWARD_SCOPE']}
  accept={'id':'BOOST','checks':checks,'reviewedSourceDigest':'a'*64}
  self.denied(s,'accept_challenge',accept)
  self.denied(s,'accept_challenge',{**accept,'reviewedSourceDigest':'b'*64},'OWNER_DECLARED')
  s=transition(s,'accept_challenge',accept,'OWNER_DECLARED')
  self.assertEqual(s['challenges']['BOOST']['reward'],'OWNED_WORLD_CHAMPION_BADGE')
  self.assertEqual(s['challenges']['BOOST']['evidenceCeiling'],'DECLARED_REVIEW_NOT_ENGINE_AUDIT')
 def gift(self,position=None):
  s=transition(self.opened(),'arrive',{'guest':'TRAVELER'},'GUEST_DECLARED')
  if position is not None:s=transition(s,'owner_position',{'position':position},'OWNER_DECLARED')
  return transition(s,'leave_gift',{'guest':'TRAVELER','id':'PARCEL','items':[{'itemId':'MIGHTY_SWORD','quantity':1}],'message':'A gift from another world'},'GUEST_DECLARED')
 def test_gift_secret_until_courier_arrives(self):
  s=self.gift();self.assertEqual(s['ownerInventory'],[])
  self.assertEqual(s['secretDepot']['PARCEL']['state'],'SECRET_DEPOT')
  self.denied(s,'claim_gift',{'id':'PARCEL'},'OWNER_DECLARED')
  s=transition(s,'advance_days',{'days':1},'OWNER_DECLARED')
  self.assertEqual(s['secretDepot']['PARCEL']['state'],'SECRET_DEPOT')
  s=transition(s,'advance_days',{'days':1},'OWNER_DECLARED')
  self.assertEqual(s['secretDepot']['PARCEL']['deliveredDay'],2)
  self.denied(s,'claim_gift',{'id':'PARCEL'})
  s=transition(s,'claim_gift',{'id':'PARCEL'},'OWNER_DECLARED')
  self.assertEqual(s['ownerInventory'],[{'itemId':'MIGHTY_SWORD','quantity':1}])
  self.denied(s,'claim_gift',{'id':'PARCEL'},'OWNER_DECLARED')
 def test_distance_and_moving_owner_change_delivery(self):
  s=self.gift([25,0]);s=transition(s,'advance_days',{'days':2},'OWNER_DECLARED')
  self.assertEqual(s['secretDepot']['PARCEL']['courierPosition'],[10,0])
  s=transition(s,'owner_position',{'position':[35,0]},'OWNER_DECLARED')
  s=transition(s,'advance_days',{'days':2},'OWNER_DECLARED')
  self.assertEqual(s['secretDepot']['PARCEL']['state'],'COURIER_TRAVEL')
  s=transition(s,'advance_days',{'days':1},'OWNER_DECLARED')
  self.assertEqual(s['secretDepot']['PARCEL']['deliveredDay'],5)
 def test_guest_can_only_leave_bound_gifts(self):
  s=self.gift()
  self.denied(s,'advance_days',{'days':100})
  self.denied(s,'owner_position',{'position':[0,0]})
  self.denied(s,'leave_gift',{'guest':'OTHER','id':'OTHER','message':'Hello'})
  self.denied(s,'leave_gift',{'guest':'TRAVELER','id':'PARCEL','message':'Duplicate'})
  self.denied(s,'leave_gift',{'guest':'TRAVELER','id':'INVALID','items':[{'itemId':'SWORD','quantity':True}]})
 def test_depot_survives_closed_receiver(self):
  s=self.gift();s=transition(s,'receiver',{'mode':'CLOSED'},'OWNER_DECLARED')
  s=transition(s,'advance_days',{'days':2},'OWNER_DECLARED')
  self.assertEqual(s['secretDepot']['PARCEL']['state'],'COURIER_ARRIVED')
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(PolicyChecks)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 p=Path(__file__).parent
 receipt={'status':'LOCAL_POLICY_TESTS_PASS' if result.wasSuccessful() else 'FAIL','version':VERSION,'testCases':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'sourceSha256':hashlib.sha256((p/'policy.py').read_bytes()).hexdigest(),'claimCeiling':'PURE_LOCAL_DECLARED_INPUT_RULE_MODEL_ONLY','actualReceiver':'CLOSED_NOT_IMPLEMENTED','networkEffects':0,'engineIntegration':'NOT_IMPLEMENTED','wholeSystemAudit':'NOT_COMPLETE'}
 (p/'CHECK_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
 raise SystemExit(0 if result.wasSuccessful() else 1)
