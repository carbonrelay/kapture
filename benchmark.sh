#!/bin/bash

# Created by argbash-init v2.8.0
# Rearrange the order of options below according to what you would like to see in the help message.
# ARG_OPTIONAL_SINGLE([mode],[m],[Mode to run the benchmark in (fast, normal, slow).  Slower tests will likely give more accurate values],[normal])
# ARG_OPTIONAL_BOOLEAN([redis],[r],[Include Redis in Kapture as part of the test],[off])
# ARG_POSITIONAL_SINGLE([max-generators],[The maximum number of generators to run as part of this test.  If the number is less than 1, it will run forever],[-1])
# ARG_HELP([Performs a benchmark of Kapture against a cluster])
# ARGBASH_GO()
# needed because of Argbash --> m4_ignore([
### START OF CODE GENERATED BY Argbash v2.8.0 one line above ###
# Argbash is a bash code generator used to get arguments parsing right.
# Argbash is FREE SOFTWARE, see https://argbash.io for more info


die()
{
	local _ret=$2
	test -n "$_ret" || _ret=1
	test "$_PRINT_HELP" = yes && print_help >&2
	echo "$1" >&2
	exit ${_ret}
}


begins_with_short_option()
{
	local first_option all_short_options='mrh'
	first_option="${1:0:1}"
	test "$all_short_options" = "${all_short_options/$first_option/}" && return 1 || return 0
}

# THE DEFAULTS INITIALIZATION - POSITIONALS
_positionals=()
_arg_max_generators="-1"
# THE DEFAULTS INITIALIZATION - OPTIONALS
_arg_mode="normal"
_arg_redis="off"


print_help()
{
	printf '%s\n' "Performs a benchmark of Kapture against a cluster"
	printf 'Usage: %s [-m|--mode <arg>] [-r|--(no-)redis] [-h|--help] [<max-generators>]\n' "$0"
	printf '\t%s\n' "<max-generators>: The maximum number of generators to run as part of this test.  If the number is less than 1, it will run forever (default: '-1')"
	printf '\t%s\n' "-m, --mode: Mode to run the benchmark in (fast, normal, slow).  Slower tests will likely give more accurate values (default: 'normal')"
	printf '\t%s\n' "-r, --redis, --no-redis: Include Redis in Kapture as part of the test (off by default)"
	printf '\t%s\n' "-h, --help: Prints help"
}


parse_commandline()
{
	_positionals_count=0
	while test $# -gt 0
	do
		_key="$1"
		case "$_key" in
			-m|--mode)
				test $# -lt 2 && die "Missing value for the optional argument '$_key'." 1
				_arg_mode="$2"
				shift
				;;
			--mode=*)
				_arg_mode="${_key##--mode=}"
				;;
			-m*)
				_arg_mode="${_key##-m}"
				;;
			-r|--no-redis|--redis)
				_arg_redis="on"
				test "${1:0:5}" = "--no-" && _arg_redis="off"
				;;
			-r*)
				_arg_redis="on"
				_next="${_key##-r}"
				if test -n "$_next" -a "$_next" != "$_key"
				then
					begins_with_short_option "$_next" && shift && set -- "-r" "-${_next}" "$@" || die "The short option '$_key' can't be decomposed to ${_key:0:2} and -${_key:2}, because ${_key:0:2} doesn't accept value and '-${_key:2:1}' doesn't correspond to a short option."
				fi
				;;
			-h|--help)
				print_help
				exit 0
				;;
			-h*)
				print_help
				exit 0
				;;
			*)
				_last_positional="$1"
				_positionals+=("$_last_positional")
				_positionals_count=$((_positionals_count + 1))
				;;
		esac
		shift
	done
}


handle_passed_args_count()
{
	test "${_positionals_count}" -le 1 || _PRINT_HELP=yes die "FATAL ERROR: There were spurious positional arguments --- we expect between 0 and 1, but got ${_positionals_count} (the last one was: '${_last_positional}')." 1
}


assign_positional_args()
{
	local _positional_name _shift_for=$1
	_positional_names="_arg_max_generators "

	shift "$_shift_for"
	for _positional_name in ${_positional_names}
	do
		test $# -gt 0 || break
		eval "$_positional_name=\${1}" || die "Error during argument parsing, possibly an Argbash bug." 1
		shift
	done
}

parse_commandline "$@"
handle_passed_args_count
assign_positional_args 1 "${_positionals[@]}"

# OTHER STUFF GENERATED BY Argbash

### END OF CODE GENERATED BY Argbash (sortof) ### ])
# [ <-- needed because of Argbash


printf "'%s' is %s\\n" 'mode' "$_arg_mode"
printf "'%s' is %s\\n" 'redis' "$_arg_redis"
printf "Value of '%s': %s\\n" 'max-generators' "$_arg_max_generators"


export mode=$_arg_mode
export redis=$_arg_redis
export max_generators=$_arg_max_generators

BASEDIR=$(dirname $0)

(
    cd $BASEDIR/benchmark
    ./benchmark.sh
)
# ] <-- needed because of Argbash