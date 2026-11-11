"""Exact reviewed v2 delta; the original engine and harness remain independently replayable."""
VERSION='assembly-contact-v2'
BASELINE='07044f8ed28748e359a3a15448478ed2d8030c16'
TARGET='Src/Orbiter/SuperVessel.cpp'
BUILDER='Tests/Production/RemainingVessels/build_native.py'
CLIENT='.github/workflows/production-client.yml'


def replace_once(body,old,new):
    if body.count(old)!=1:raise ValueError('One exact preserved source anchor required: '+old[:100])
    return body.replace(old,new,1)


def corrected_physics(body):
    a='\tAddSurfaceForces (&F, &M, &state, tfrac, dt); // add ground contact forces and moments'
    b='vlist[comp].vessel->AddSurfaceForces (&Fcomp, &Mcomp, &scomp, tfrac, dt)'
    c='\tsp.is_in_atm        = false;'
    body=replace_once(body,c,c+'\n\tUpdateProxies();\n\tUpdateSurfParams();')
    body=replace_once(body,a,'\tcollision_during_update |=\n\t'+a)
    return replace_once(body,b,b[:-1]+', update_with_collision)')


def versioned_builder(body):
    body=replace_once(body,"    p.add_argument('--jobs',type=int,default=4)","    p.add_argument('--physics-version',choices=('original','assembly-contact-v2'),default='original')\n    p.add_argument('--jobs',type=int,default=4)")
    body=replace_once(body,'    extraction_source.verify()',"    physics_proof=None\n    if a.physics_version=='original':extraction_source.verify()\n    else:\n        from PhysicsV2 import source as physics_source\n        physics_proof=physics_source.verify()")
    anchor='    for module in list(sys.modules.values()):'
    body=replace_once(body,anchor,"    if physics_proof:inputs.update(physics_source.INPUTS)\n"+anchor)
    anchor="    manifest=a.output/'build.json'"
    body=replace_once(body,anchor,"    if physics_proof:report.update(physics_version=a.physics_version,physics_source_proof=physics_proof)\n"+anchor)
    anchor="        notice=engine/'NativeModules/Licenses/implot-LICENSE.txt'"
    body=replace_once(body,anchor,"        if physics_proof:\n            sdk_header=engine/'native-sdk/OrbiterNativeBuild.h'\n            require(sdk_header.is_file(),'Exact generated v2 SDK input required')\n            runtime.append(sdk_header)\n"+anchor)
    return body


def versioned_client(body):
    old="      retain_stock_sdk:\n        type: boolean\n        default: false"
    body=replace_once(body,old,old+"\n      physics_version:\n        type: string\n        default: 'original'")
    old='          python Tests/Production/observation_source.py'
    new="""          if ('${{ inputs.physics_version }}' -eq 'assembly-contact-v2') {
            python -B Tests/Production/PhysicsV2/source.py --output out/physics-v2-source.json
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          } elseif ('${{ inputs.physics_version }}' -eq '' -or '${{ inputs.physics_version }}' -eq 'original') {
            python Tests/Production/observation_source.py
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
          } else { throw 'Unknown explicitly selected physics version' }"""
    body=replace_once(body,old,new)
    old='      - uses: actions/cache@v6\n        id: dxsdk'
    new="""      - name: Preserve explicit physics version and unchanged original source audit
        if: inputs.physics_version == 'assembly-contact-v2'
        uses: actions/upload-artifact@v7
        with:
          name: physics-v2-source-${{ matrix.configuration }}
          retention-days: 14
          path: |
            out/physics-v2-source.json
            out/physics-v2-baseline/*.json
            out/physics-v2-baseline/*.log
"""+old
    return replace_once(body,old,new)
