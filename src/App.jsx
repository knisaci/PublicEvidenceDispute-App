import { useState, useEffect } from 'react'
import { createClient } from 'genlayer-js'
import { testnetBradbury } from 'genlayer-js/chains'
import './App.css'

const CONTRACT = '0xca898F1791B1e93028D7aA3a3DE813D3B1f58B93'
const readClient = createClient({ chain: testnetBradbury })

function short(addr) {
  if (!addr) return '—'
  const s = String(addr)
  return s.slice(0, 6) + '…' + s.slice(-4)
}

function gen(wei) {
  return (Number(wei || 0) / 1e18).toFixed(4) + ' GEN'
}

function App() {
  const [account, setAccount] = useState(null)
  const [d, setD] = useState(null)
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [amount, setAmount] = useState('0.1')
  const [defClaim, setDefClaim] = useState('BA287 was delayed on 2026-08-15')
  const [defUrl, setDefUrl] = useState('https://www.flightradar24.com/data/flights/ba287')

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

  async function sendTx(name, args, value, waitMs, okMsg) {
    if (!account) return alert('Connect wallet first')
    setLoading(true)
    setStatus('Sending ' + name + '…')
    try {
      const client = createClient({ chain: testnetBradbury, account, provider: window.ethereum })
      try { await client.connect('testnetBradbury') } catch {}
      const tx = await client.writeContract({
        address: CONTRACT,
        functionName: name,
        args,
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
        <div className="badge">GenLayer · Two-sided evidence court</div>
        <h1>Public Evidence Dispute</h1>
        <p className="sub">Each party commits a claim and an evidence URL. Those commits are immutable. Resolve only after both sides have locked their case.</p>
      </header>

      <section className="card hero">
        <div className={'pill ' + pill}>{pill}</div>
        <p className="question">{d?.topic || 'Loading…'}</p>
      </section>

      <section className="grid2">
        <div className="card">
          <h2>Creator (locked)</h2>
          <div className="rows">
            <div><span>Address</span><b>{short(d?.creator)}</b></div>
            <div><span>Committed</span><b>{d?.creator_committed ? 'yes' : 'no'}</b></div>
            <div><span>Stake</span><b>{d ? gen(d.creator_stake) : '—'}</b></div>
          </div>
          <p className="note">{d?.creator_claim || '—'}</p>
          {d?.creator_evidence_url && <a className="link" href={d.creator_evidence_url} target="_blank" rel="noreferrer">{d.creator_evidence_url}</a>}
        </div>
        <div className="card">
          <h2>Defendant</h2>
          <div className="rows">
            <div><span>Address</span><b>{short(d?.defendant)}</b></div>
            <div><span>Committed</span><b>{d?.defendant_committed ? 'yes' : 'no'}</b></div>
            <div><span>Stake</span><b>{d ? gen(d.defendant_stake) : '—'}</b></div>
          </div>
          <p className="note">{d?.defendant_claim || 'Not committed yet'}</p>
          {d?.defendant_evidence_url && <a className="link" href={d.defendant_evidence_url} target="_blank" rel="noreferrer">{d.defendant_evidence_url}</a>}
        </div>
      </section>

      <section className="card">
        <h2>Pot / verdict</h2>
        <div className="stat">{d ? gen(d.pot) : '—'}</div>
        <div className="rows">
          <div><span>Verdict</span><b>{d?.verdict || '—'}</b></div>
          <div><span>Confidence</span><b>{d?.confidence || '—'}</b></div>
          <div><span>Winner</span><b>{short(d?.winner)}</b></div>
          <div><span>Paid / refunded</span><b>{d?.is_paid ? 'paid' : d?.is_refunded ? 'refunded' : 'no'}</b></div>
        </div>
        <p className="note">{d?.note || 'No note yet.'}</p>
      </section>

      <section className="card">
        <h2>Actions</h2>
        {!account ? (
          <button className="primary" onClick={connect}>Connect wallet</button>
        ) : (
          <>
            <p className="wallet">{short(account)}{isCreator ? ' · creator' : ''}{isDefendant ? ' · defendant' : ''}</p>

            {isDefendant && d && !d.defendant_committed && !d.has_resolved && (
              <div className="action">
                <h3>Commit defense (immutable)</h3>
                <p className="hint">This can be set only once. Resolve is blocked until it is set.</p>
                <input value={defClaim} onChange={e => setDefClaim(e.target.value)} placeholder="Defendant claim" />
                <div className="row" style={{marginTop: 8}}>
                  <input value={defUrl} onChange={e => setDefUrl(e.target.value)} placeholder="https:// evidence" />
                  <button className="primary" disabled={loading} onClick={() => sendTx('commit_defense', [defClaim, defUrl], 0n, 25000, 'Defense committed')}>Commit</button>
                </div>
              </div>
            )}

            <div className="action">
              <h3>Stake</h3>
              <div className="row">
                <input type="number" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} />
                <button disabled={loading || !(isCreator || isDefendant)} onClick={() => sendTx('add_stake', [], wei(), 25000, 'Stake added')}>Add stake</button>
              </div>
              {isDefendant && Number(d?.defendant_stake || 0) === 0 && (
                <button className="primary" disabled={loading} onClick={() => sendTx('join_as_defendant', [], wei(), 25000, 'Defendant joined')}>Join as defendant</button>
              )}
            </div>

            {d && d.creator_committed && d.defendant_committed && Number(d.creator_stake) > 0 && Number(d.defendant_stake) > 0 && !d.has_resolved && (
              <div className="action">
                <h3>Resolve</h3>
                <p className="hint">Validators fetch both committed evidence URLs.</p>
                <button className="primary" disabled={loading} onClick={() => sendTx('resolve', [], 0n, 90000, 'Resolve sent')}>Resolve</button>
              </div>
            )}

            {d?.has_resolved && !d.is_paid && !d.is_refunded && (
              <button className="primary" disabled={loading} onClick={() => sendTx('settle', [], 0n, 25000, 'Settled')}>Settle</button>
            )}

            {d && !d.has_resolved && Number(d.defendant_stake) === 0 && isCreator && (
              <div className="action">
                <h3>Cancel open</h3>
                <button disabled={loading} onClick={() => sendTx('cancel_open', [], 0n, 25000, 'Cancelled')}>Cancel open</button>
              </div>
            )}

            {d && !d.has_resolved && (isCreator || isDefendant) && (
              <div className="action">
                <button disabled={loading} onClick={() => sendTx('request_cancel', [], 0n, 25000, 'Cancel requested')}>Request cancel</button>
                <button disabled={loading} onClick={() => sendTx('cancel_expired', [], 0n, 25000, 'Expired cancel sent')}>Cancel expired</button>
              </div>
            )}
          </>
        )}
        {status && <p className="status">{status}</p>}
      </section>

      <footer>
        <div>Contract · {CONTRACT}</div>
        <div>Testnet Bradbury · both claims locked before resolve</div>
      </footer>
    </div>
  )
}

export default App
