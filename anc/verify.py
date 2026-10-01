"""Reproduce the theoretical examples. Python 3, standard library only.
All inputs are synthetic. This is not a GPU benchmark or a causal estimate.
Run from this file's directory or from the manuscript directory.
"""
from pathlib import Path
from math import exp, expm1, log, isclose
import json
import random

ROOT = Path(__file__).resolve().parent.parent

def retirement(tiers, c, salvage, rho):
    m = c + rho * salvage
    return max([0.] + [log(R/m)/d for R, d in tiers])

def revenue(t, tiers):
    return max(R * exp(-d*t) for R,d in tiers)

def integral(t0, t1, tiers, c, rho):
    """Exact discounted best-use cash flow, discounted from t0."""
    cuts = [t0,t1]
    for R,d in tiers:
        if c > 0:
            x = log(R/c)/d
            if t0 < x < t1: cuts.append(x)
    for i,(R,d) in enumerate(tiers):
        for R2,d2 in tiers[i+1:]:
            if d != d2:
                x=log(R/R2)/(d-d2)
                if t0 < x < t1: cuts.append(x)
    cuts=sorted(set(cuts))
    val=0.
    for a,b in zip(cuts,cuts[1:]):
        mid=(a+b)/2
        R,d=max(tiers,key=lambda v:v[0]*exp(-v[1]*mid))
        if R*exp(-d*mid) > c:
            val += R*exp(-d*a)*exp(-rho*(a-t0))*(-expm1(-(rho+d)*(b-a)))/(rho+d)
            val -= c*exp(-rho*(a-t0))*(-expm1(-rho*(b-a)))/rho
    return val

def grid_dp(tiers,c,S,rho):
    """Backward optimization with operation, idle and scrap alternatives."""
    # Gross revenue below carrying cost makes all later operation inferior.
    end=1.
    while revenue(end,tiers)>c+rho*S: end*=2
    end+=1
    steps=4000
    dt=end/steps
    value=S
    chosen=steps
    for n in range(steps-1,-1,-1):
        hold=integral(n*dt,(n+1)*dt,tiers,c,rho)+exp(-rho*dt)*value
        if S>=hold:
            value=S
            chosen=n
        else:
            value=hold
    return chosen*dt,value,dt

def hazard(t,d):
    x=d*t
    survival=.99*exp(-10*x)+.01*exp(-.01*x)
    density=9.9*exp(-10*x)+.0001*exp(-.01*x)
    return d*density/survival

def run():
    rho=.1; c=.25; S=2.5
    cases={}
    for label,g,gamma in [('baseline',.04,.12),('improved',.08,.14)]:
        d=gamma-g
        T=retirement([(1,d)],c,S,rho)
        cases[label]={'g':g,'gamma':gamma,'d':d,'hazard':d,
                      'mean_life':1/d,'life_at_buffer_log2':T,
                      'survival_10':exp(-10*d),
                      'value_at_time_0':integral(0,T,[(1,d)],c,rho)+exp(-rho*T)*S}
        for k in range(301):
            t=k/10
            old_supply=exp(-d*t)*exp(g*t)
            price=exp(-gamma*t)
            demand=2/price
            leased=demand-old_supply
            assert leased>0
            assert isclose(old_supply+leased,demand,rel_tol=1e-12)
            assert isclose(price*leased-exp(-gamma*t)*leased,0.,abs_tol=1e-12)
    assert isclose(cases['improved']['life_at_buffer_log2']/cases['baseline']['life_at_buffer_log2'],4/3)
    assert isclose(cases['improved']['hazard']/cases['baseline']['hazard'],.75)
    migration={}
    for label,db in [('baseline',.10),('improved',.05)]:
        tiers=[(2.,.20),(1.5,db)]
        T=retirement(tiers,.5,5.,rho)
        migration[label]={'retirement':T,'switch':log(2/1.5)/(.2-db)}
        # Positive residual supply even when all legacy mass uses a single tier.
        for n in range(301):
            t=n/10
            for q0,g in [(2.,.1),(1.5,.3-db)]:
                assert 3*exp(.3*t)>q0*exp(g*t)
    rng=random.Random(20261001)
    errors=[]; value_errors=[]
    for n in range(100):
        tiers=[(rng.uniform(.1,3),rng.uniform(.04,.5)) for _ in range(rng.randint(1,4))]
        cost=rng.uniform(.1,1.2); salvage=rng.uniform(.2,5); discount=rng.uniform(.03,.2)
        T=retirement(tiers,cost,salvage,discount)
        Td,Vd,dt=grid_dp(tiers,cost,salvage,discount)
        assert abs(Td-T)<=dt*1.001,(n,T,Td,dt)
        exact=integral(0,T,tiers,cost,discount)+exp(-discount*T)*salvage
        assert Vd<=exact+1e-9
        # Bound quadrature-free grid loss by the missed interval's discounted margin.
        assert exact-Vd<.001
        errors.append(abs(Td-T)/dt); value_errors.append(exact-Vd)
        # Improvement may affect all or only one tier; the strict criterion is checked directly.
        improved=[(R*rng.uniform(1,1.5),d*rng.uniform(.5,1)) for R,d in tiers]
        T2=retirement(improved,cost,salvage,discount)
        assert T2>=T-1e-10
        assert (T2>T+1e-9)==(revenue(T,improved)>cost+discount*salvage+1e-9)
    # Value formula vs exact integration and Bellman equation away from exit.
    value_residuals=[]
    for d in [.04,.08,.2]:
        T=retirement([(1.,d)],c,S,rho)
        for fraction in [.0,.2,.7,.95]:
            t=T*fraction; b=exp(-d*t); tau=T-t
            val=b*(1-exp(-(rho+d)*tau))/(rho+d)-c*(1-exp(-rho*tau))/rho+S*exp(-rho*tau)
            independent=integral(t,T,[(1.,d)],c,rho)+S*exp(-rho*tau)
            assert isclose(val,independent,abs_tol=1e-11)
            def value_at(x):
                return integral(x,T,[(1.,d)],c,rho)+S*exp(-rho*(T-x))
            h=1e-5
            derivative=(value_at(t+h)-value_at(t-h))/(2*h)
            residual=abs(derivative-(rho*val-(b-c)))
            assert residual<1e-8
            value_residuals.append(residual)
    # Uniform gains cancel; a differential level gain changes lifetime logarithmically.
    for G,H in [(2,2),(2,1.5),(1.5,2)]:
        T=retirement([(G/H,.08)],c,S,rho)
        assert isclose(T-retirement([(1,.08)],c,S,rho),log(G/H)/.08,abs_tol=1e-10)
    # Independent cohort integration over uniform quantiles: Z=-log(1-u).
    count=100000
    for d in [.08,.06]:
        fraction=sum(-log(1-(n+.5)/count)/d>10 for n in range(count))/count
        assert abs(fraction-exp(-d*10))<=1/count
    # Longer lives can coexist with a HIGHER contemporaneous hazard.
    mixed={'d_1_at_t_1':hazard(1,1),'d_half_at_t_1':hazard(1,.5)}
    assert mixed['d_half_at_t_1']>mixed['d_1_at_t_1']
    with (ROOT/'survival.dat').open('w') as f:
        f.write('t baseline improved\n')
        for n in range(301):
            t=n/10; f.write(f'{t:.1f} {exp(-.08*t):.12f} {exp(-.06*t):.12f}\n')
    result={'status':'PASS','synthetic':True,'cohort':cases,'migration':migration,
            'mixed_hazard_counterexample':mixed,'dp_cases':100,
            'max_dp_time_error_in_grid_intervals':max(errors),
            'max_dp_value_error':max(value_errors),
            'max_bellman_residual':max(value_residuals),
            'market_grid_points_per_regime':301,'cohort_quantiles_per_regime':count,
            'limitations':'Implementation checks, not empirical validation or novelty review.'}
    (Path(__file__).resolve().parent/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': run()
