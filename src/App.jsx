import { useState, useEffect } from 'react'
import { createClient } from 'genlayer-js'
import { testnetBradbury } from 'genlayer-js/chains'
import './App.css'

const CONTRACT = '0x4A7050418a9dFe41709400FbC85F8C8A1f593aE6'
const readClient = createClient({ chain: testnetBradbury })

function short(addr) {
  if (!addr) return '—'
  const s = String(addr)
  return s.slice(0, 6) + '…' + s.slice(-4)
}

function gen(wei) {
  const n = Number(wei || 0) / 1e18
  return n.toFixed(4) + ' GEN'
}

function App() {
  const [account, setAccount] = useState(null)
  const [d, setD] = useState(null)
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [amount, setAmount] = useState('0.1')

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const result = await readClient.readContract({
        address: CONTRACT,
        functionName: 'get_dispute',
        args: [],
      })
      setD(result)
    } catch (e) {
      console.error(e)
    }
  }

  async function connect() {
    if (!window.ethereum) return alert('Install MetaMask')
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' })
    setAccount(accounts[0])
  }

  function writeClient() {
    return createClient({ chain: testnetBradbury, account, provider: window.ethereum })
  }

  async function sendTx(name, value, waitMs, okMsg) {
    if (!account) return alert('Connect wallet first')
    setLoading(true)
    setStatus('Sending ' + name + '…')
    try {
      const client = writeClient()
      try { await client.connect('testnetBradbury') } catch {}
      const tx = await client.writeContract({
        address: CONTRACT,
        functionName: name,
        args: [],
        value,
      })
      setStatus('Tx ' + String(tx).slice(0, 12) + '… waiting')
      setTimeout(() => { load(); setLoading(false); setStatus(okMsg) }, waitMs)
    } catch (e) {
      setStatus('Error: ' + (e.message || 'failed'))
      setLoading(false)
    }
  }

  const wei = () => BigInt(Math.floor(Number(amount) * 1e18))
  const isCreator = account && d && account.toLowerCase() === String(d.creator || '').toLowerCase()
  const isDefendant = account && d && account.toLowerCase() === String(d.defendant || '').toLowerCase()
  const pill = d?.status || 'loading'

  return (
    <div className="app">
      <div className="glow" />
      <header>
        <div className="badge">GenLayer · Public Evidence Court</div>
        <h1>Public Evidence Dispute</h1>
        <p className="sub">Two parties stake GEN. Validators read a public page. Winner takes the pot — or both get refunded.</p>
      </header>

      <section className="card hero">
        <div className={'pill ' + pill}>{pill}</div>
        <p className="question">{d?.question || 'Loading dispute…'}</p>
        {d?.evidence_url && (
          <a className="link" href={d.evidence_url} target="_blank" rel="noreferrer">{d.evidence_url}</a>
        )}
      </section>

      <section className="grid2">
        <div className="card">
          <h2>Pot</h2>
          <div className="stat">{d ? gen(d.pot) : '—'}</div>
          <div className="rows">
            <div><span>Creator stake</span><b>{d ? gen(d.creator_stake) : '—'}</b></div>
            <div><span>Defendant stake</span><b>{d ? gen(d.defendant_stake) : '—'}</b></div>
            <div><span>Expires unix</span><b>{d ? String(d.expires_unix) : '—'}</b></div>
          </div>
        </div>
        <div className="card">
          <h2>Parties</h2>
          <div className="rows">
            <div><span>Creator</span><b>{short(d?.creator)}</b></div>
            <div><span>Defendant</span><b>{short(d?.defendant)}</b></div>
            <div><span>Creator cancel</span><b>{d?.creator_cancel ? 'yes' : 'no'}</b></div>
            <div><span>Defendant cancel</span><b>{d?.defendant_cancel ? 'yes' : 'no'}</b></div>
          </div>
        </div>
      </section>

      <section className="card">
        <h2>Verdict</h2>
        <div className="rows">
          <div><span>Verdict</span><b>{d?.verdict || '—'}</b></div>
          <div><span>Confidence</span><b>{d?.confidence || '—'}</b></div>
          <div><span>Winner</span><b>{short(d?.winner)}</b></div>
          <div><span>Paid / refunded</span><b>{d?.is_paid ? 'paid' : d?.is_refunded ? 'refunded' : 'no'}</b></div>
        </div>
        <p className="note">{d?.note || 'No resolution note yet.'}</p>
      </section>

      <section className="card">
        <h2>Actions</h2>
        {!account ? (
          <button className="primary" onClick={connect}>Connect wallet</button>
        ) : (
          <>
            <p className="wallet">
              {short(account)}
              {isCreator ? ' · creator' : ''}
              {isDefendant ? ' · defendant' : ''}
            </p>

            <div className="action">
              <h3>Stake</h3>
              <div className="row">
                <input type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} />
                <button disabled={loading || !(isCreator || isDefendant)} onClick={() => sendTx('add_stake', wei(), 25000, 'Stake added')}>
                  Add stake
                </button>
              </div>
              {isDefendant && d?.status === 'open' && (
                <button className="primary" disabled={loading} onClick={() => sendTx('join_as_defendant', wei(), 25000, 'Defendant joined')}>
                  Join as defendant
                </button>
              )}
            </div>

            {d && !d.has_resolved && d.creator_stake > 0 && d.defendant_stake > 0 && (
              <div className="action">
                <h3>Resolve</h3>
                <p className="hint">Five validators fetch the evidence page and must match verdict + confidence.</p>
                <button className="primary" disabled={loading} onClick={() => sendTx('resolve', 0n, 90000, 'Resolution submitted')}>Resolve</button>
              </div>
            )}

            {d?.has_resolved && !d.is_paid && !d.is_refunded && (
              <div className="action">
                <h3>Settle</h3>
                <button className="primary" disabled={loading} onClick={() => sendTx('settle', 0n, 25000, 'Settled')}>Settle</button>
              </div>
            )}

            {d && !d.has_resolved && d.status === 'open' && isCreator && (
              <div className="action">
                <h3>Cancel open</h3>
                <p className="hint">Defendant never funded. Return creator stake.</p>
                <button disabled={loading} onClick={() => sendTx('cancel_open', 0n, 25000, 'Cancelled')}>Cancel open</button>
              </div>
            )}

            {d && !d.has_resolved && (d.status === 'open' || d.status === 'funded') && (isCreator || isDefendant) && (
              <div className="action">
                <h3>Request cancel</h3>
                <p className="hint">Both parties must request. Then each recorded stake is returned.</p>
                <button disabled={loading} onClick={() => sendTx('request_cancel', 0n, 25000, 'Cancel requested')}>Request cancel</button>
              </div>
            )}

            {d && !d.has_resolved && (d.status === 'open' || d.status === 'funded') && (isCreator || isDefendant) && (
              <div className="action">
                <h3>Cancel expired</h3>
                <p className="hint">After expires_unix, either party can unwind.</p>
                <button disabled={loading} onClick={() => sendTx('cancel_expired', 0n, 25000, 'Expired cancel sent')}>Cancel expired</button>
              </div>
            )}
          </>
        )}
        {status && <p className="status">{status}</p>}
      </section>

      <footer>
        <div>Contract · {CONTRACT}</div>
        <div>Testnet Bradbury</div>
      </footer>
    </div>
  )
}

export default App
