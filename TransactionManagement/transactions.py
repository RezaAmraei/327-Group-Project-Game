import threading
import time
import uuid
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

#transaction = 3 states
# Begin, Commit, Abort

class TransactionStatus(Enum):
    BEGIN = auto()
    COMMITTED = auto()
    ABORTED = auto()
    
@dataclass
class Transaction:
    transaction_id: str
    status: TransactionStatus = TransactionStatus.BEGIN
    writes: Dict[str, Any] = field(default_factory=dict)
    #ugly code but this is an example of what it looks like
    #writes = {
        #"winner": {"player_id": "player_A", "timestamp": 123456.78}
    #}
    version_snapshot: Dict[str, int] = field(default_factory= dict)
    
class TransactionManager:
    def __init__(self):
        #protect all shared resources with a lock
        self._lock = threading.Lock()
        
        #store commited resources
        # Example later: resource_id "winner" -> {"value": {...}, "version": 0}
        self._resources: Dict[str, Dict[str, Any]] = {}
        
        #store all transcations by id
        self._transactions: Dict[str, Transaction] = {}
        
    #start a new transaction and return its id
    def begin(self) -> str:
        #create unique id
        transaction_id = f"tx-{uuid.uuid4().hex}"
        
        #create transaction object
        new_transaction = Transaction(transaction_id= transaction_id)
        
        #store in the manager
        with self._lock:
            self._transactions[transaction_id] = new_transaction
            
        return transaction_id
    
    #setting inital value for resource
    def set_resource_initial(self, resource_id: str, value: Any) -> None:
        with self._lock:
            self._resources[resource_id] = {
                "value": value,
                "version": 0
            }
    
    #get value of the resource
    def get_resource(self, resource_id: str) -> Any:
        with self._lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return None
            return resource["value"]
        
    
    #read resource within the transaction
    def read(self, transaction_id: str, resource_id: str) -> Any:
        with self._lock:
            #chech is tranasction exist
            tx = self._transactions.get(transaction_id)
            if tx is None:
                raise RuntimeError(f"Transaction {transaction_id} does not exist.")
            
            #make sure it hasnt been aborted or commited already
            if tx.status != TransactionStatus.BEGIN:
                raise RuntimeError(f"Transaction {transaction_id} is not active.")
            
            #if the tranasction already wrote to this resuroce, return that value
            if resource_id in tx.writes:
                return tx.writes[resource_id]
            
            #else, read commited value
            resource = self._resources.get(resource_id)
            if resource is None:
                value = None
                version = 0
            else:
                value = resource["value"]
                version = resource["version"]
                
            #record version
            if resource_id not in tx.version_snapshot:
                tx.version_snapshot[resource_id] = version
                
            return value
        
    #write resource within the transaction
    def write(self, transaction_id: str, resource_id: str, value: Any) -> None:
        #check if transaction exist
        with self._lock:
            tx = self._transactions.get(transaction_id)
            if tx is None:
                raise RuntimeError(f"Transaction {transaction_id} does not exist.")
            
            #make sure it hasnt been aborted or commited
            if tx.status != TransactionStatus.BEGIN:
                raise RuntimeError(f"Transaction {transaction_id} is not active.")
            
            #if this is the first time the transaction touches this resource
            #then record the current version 
            
            if resource_id not in tx.version_snapshot:
                resource = self._resources.get(resource_id)
                if resource is None:
                    version = 0
                else:
                    version = resource["version"]
                tx.version_snapshot[resource_id] = version
                
            tx.writes[resource_id] = value
            
    #commit tranasction
    def commit(self, transaction_id: str) -> bool:
        with self._lock:
            #check if transaction exist
            tx = self._transactions.get(transaction_id)
            if tx is None:
                raise RuntimeError(f"transaction {transaction_id} does not exist.")
            
            #only alow a commit form the begin state
            if tx.status != TransactionStatus.BEGIN:
                return False
            
            #conflict detectioon
            for resource_id, snap_version in tx.version_snapshot.items():
                current = self._resources.get(resource_id)
                if current is None:
                    current_version = 0
                else:
                    current_version = current["version"]
                
                #if version chhanged since the snapshot, someone elser has touched it
                if current_version != snap_version:
                    #abort the tranaction
                    tx.status = TransactionStatus.ABORTED
                    tx.writes.clear()
                    tx.version_snapshot.clear()
                    return False
                
            #no conflict, apply writes
            for resource_id, new_value in tx.writes.items():
                current = self._resources.get(resource_id)
                if current is None:
                    #new resource
                    self._resources[resource_id] = {
                        "value": new_value,
                        "version": 1
                    }
                else:
                    #update existing resource
                    current["value"] = new_value
                    current["version"] += 1
                
            #mark tranaction as commited
            tx.status = TransactionStatus.COMMITTED
            return True
    
    # abort function
    def abort(self, transaction_id: str) -> None:
        with self._lock:
            tx = self._transactions.get(transaction_id)
            if tx is None:
                # transaction doesnt exist
                return

            # if its still in the begin state, mark it aborted and clear
            if tx.status == TransactionStatus.BEGIN:
                tx.status = TransactionStatus.ABORTED
                tx.writes.clear()
                tx.version_snapshot.clear()
            
class GameState:
    WINNER_KEY = "winner"
    def __init__(self, tx_manager: Optional[TransactionManager] = None):
        #use if existing TranactionManager if passed in, otherwise create new
        self.tx_manager = tx_manager or TransactionManager()
        
        #make sure the winner resource exist and starts as none
        self.tx_manager.set_resource_initial(self.WINNER_KEY, None)
        
    #return offical winner
    def get_committed_winner(self) -> Any:
        return self.tx_manager.get_resource(self.WINNER_KEY)
    
    #declare player winner using tranaction
    def declare_winner_transactional(self, player_id: str)-> bool:
        transaction_id = self.tx_manager.begin()
        
        try:
            #read winner in transaction
            current_winner = self.tx_manager.read(transaction_id, self.WINNER_KEY)
            
            #if someone has already won, abort
            if current_winner is not None:
                self.tx_manager.abort(transaction_id)
                return False

            #new winner valye
            winner_record = {
                "player_id": player_id,
                "timestamp": time.time()
            }
            
            self.tx_manager.write(transaction_id, self.WINNER_KEY, winner_record)
            
            #commit
            committed = self.tx_manager.commit(transaction_id)
            
            if not committed:
                return False
            
            return True
        
        except Exception:
            #if unknown errors, abort to be safe
            self.tx_manager.abort(transaction_id)
            raise
        
#TESTING DEMO CODE

def _player_win_attempt(game_state: GameState, player_id: str, delay: float = 0.0):
    """
    Simulate a player trying to declare themselves as the winner
    after some delay.
    """
    time.sleep(delay)
    success = game_state.declare_winner_transactional(player_id)
    status = "WON" if success else "LOST (transaction aborted)"
    print(f"[{player_id}] attempt finished -> {status}")


if __name__ == "__main__":
    # simple test / demo
    game_state = GameState()

    # two players trying to win "at the same time"
    t1 = threading.Thread(target=_player_win_attempt, args=(game_state, "player_A", 0.1))
    t2 = threading.Thread(target=_player_win_attempt, args=(game_state, "player_B", 0.1))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print("Final committed winner:", game_state.get_committed_winner())