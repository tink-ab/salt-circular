import json
import sys
from itertools import chain


def main():
    if len(sys.argv) != 2:
        print "Usage: {0} <jsonfile>".format(sys.argv[0])
        print
        print "Extract the json file using something like:"
        print
        print "    salt --out=json YOURMINION state.show_highstate"
        print
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    assert len(data) == 1, "Expected only a single host to match."
    data = data.values()[0]

    types_by_name = dict()
    for k, v in data.items():
        types_by_name[k] = types_by_name.get(k, []).append([k for k in v.keys() if not k.startswith('__')][0])

    deps = list(flatten((dependencies(k, v, types_by_name) for k, v in data.items())))
    print "Found {0} state dependencies:".format(len(deps))
    print
    for state, requisite in deps:
        print " * State {0} depends on state {1}.".format(pretty_tuple(state), pretty_tuple(requisite))
    print

    print "Searching for circular dependencies. Reducing until can't be reduced anymore..."
    iteration=1
    while True:
        states = set([k[0] for k in deps])
        depends_on = set([k[1] for k in deps])
        can_be_reduced = depends_on - states
        if not can_be_reduced:
            break

        to_remove = iter(can_be_reduced).next()
        print "Iteration: {0:>5}\tLeft to apply: {1:>5}\tService to 'apply': {2}".format(iteration, len(deps), pretty_tuple(to_remove))
        deps = [dep for dep in deps if to_remove not in dep]

        iteration += 1
    print "Reduction done."

    print
    if deps:
        print "THERE WERE CIRCULAR DEPENDENCIES (AKA, you have a bad day!):"
        print
        for dep in deps:
            print pretty_tuple(dep)
    else:
        print "No circular dependency found."


def dependencies(statename, states, types_by_name):
    """Generates (state, what_it_depends_on) list."""
    statetypes = [k for k in states.keys() if not k.startswith('__')]
    for statetype in statetypes:
        data = states[statetype]

        # Extract all dependencies from this state.
        for dataitem in data:
            if isinstance(dataitem, dict):
                assert len(dataitem)==1
                if dataitem.keys()[0] in ('require', 'watch', 'onchanges', 'onfail'):
                    for dep in dataitem.values()[0]:
                        if isinstance(dep, dict):
                            for k, v in dep.items():
                                yield ((statetype, statename), (k, v))
                        else:
                            for name in types_by_name.get(dep, []):
                                yield ((statetype, statename), (name, dep))
                if dataitem.keys()[0] in ('require_in', 'watch_in', 'prereq'):
                    for dep in dataitem.values()[0]:
                        if isinstance(dep, dict):
                            for k, v in dep.items():
                                yield ((k, v), (statetype, statename))
                        else:
                            for name in types_by_name.get(dep, []):
                                yield ((name, dep), (statetype, statename))


def pretty_tuple(t):
    return "({0}, {1})".format(t[0], t[1])


def flatten(listOfLists):
    "Flatten one level of nesting"
    return chain.from_iterable(listOfLists)


if __name__=="__main__":
    main()
