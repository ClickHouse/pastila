" plugin/pastila.vim — Vim plugin for pastila.nl

if exists('g:loaded_pastila')
    finish
endif
let g:loaded_pastila = 1

let s:script_dir = fnamemodify(resolve(expand('<sfile>:p')), ':h:h')
let s:pastila_py = s:script_dir . '/pastila.py'

function! s:LineEnding(ff)
    if a:ff ==# 'dos'
        return "\r\n"
    elseif a:ff ==# 'mac'
        return "\r"
    endif
    return "\n"
endfunction

function! s:PastilaUpload() range
    let l:eol = s:LineEnding(&fileformat)
    let l:lines = join(getline(a:firstline, a:lastline), l:eol) . l:eol
    let l:output = system('python3 ' . shellescape(s:pastila_py), l:lines)
    if v:shell_error
        echohl ErrorMsg
        echom 'Pastila upload failed: ' . l:output
        echohl None
    else
        let l:url = substitute(l:output, '[\r\n]\+$', '', '')
        let @+ = l:url
        echo 'Pastila: ' . l:url . ' (copied to clipboard)'
    endif
endfunction

function! s:PastilaDownload(url)
    let l:output = system('python3 ' . shellescape(s:pastila_py) . ' ' . shellescape(a:url))
    if v:shell_error
        echohl ErrorMsg
        echom 'Pastila download failed: ' . l:output
        echohl None
    else
        new
        setlocal buftype=nofile bufhidden=wipe noswapfile
        put! =l:output
        " Remove trailing empty line left by put
        $delete _
    endif
endfunction

command! -range=% PastilaUpload <line1>,<line2>call s:PastilaUpload()
command! -nargs=1 PastilaDownload call s:PastilaDownload(<q-args>)
